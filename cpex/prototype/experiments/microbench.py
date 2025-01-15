import time, os, asyncio
from cpex.helpers import misc, http, files
from cpex.crypto import libcpex, groupsig
from pylibcpex import Oprf, Utils
from cpex import config, constants
from cpex.models import cache
from multiprocessing import Pool


numIters = 1000


# Sample src, dst and JWT token
src = '16841333538'
dst = '16847000540'
token = "eyJhbGciOiJFUzI1NiIsInBwdCI6InNoYWtlbiIsInR5cCI6InBhc3Nwb3J0IiwieDV1IjoiaHR0cDovL2NlcnQtcmVwby9jZXJ0cy9zcF8xIn0.eyJpYXQiOjE3MzQ4OTU2NjMsImF0dGVzdCI6IkMiLCJvcmlnIjp7InRuIjpbIjE2ODQxMzMzNTM4Il19LCJkZXN0Ijp7InRuIjpbIjE2ODQ3MDAwNTQwIl19fQ.7xC7RuEnCAp62ZSvmtWsZ3Hco-bvT9EU-JoFk48HzINCh4GLaDTR8o7S042TrB5cWK6kCwSMjddoiH5JUExB3g"

# OPRF keys for server 1 and server 2
Keypairs = [Oprf.keygen() for _ in range(config.OPRF_EV_PARAM)]

def toMs(seconds):
    return round(seconds * 1000, 3)

def benchCpexProtocol(printResults=True):
    call_id_time = 0
    evaluator_time = 0
    provider_enc_sign_time = 0
        
    # Begin Call ID Generation
    call_id_time = time.perf_counter()
    call_details = libcpex.normalize_call_details(src=src, dst=src)
    requests, masks = libcpex.create_evaluation_requests(call_details)
    call_id_time = time.perf_counter() - call_id_time
    
    responses = []
    evaluator_time = time.perf_counter()
    for i, req in enumerate(requests):
        gpk = groupsig.get_gpk()
        groupsig.verify(requests[0]['data']['sig'], str(requests[0]['data']['i_k']) + requests[0]['data']['x'], gpk=gpk)
        (fx, vk) = Oprf.evaluate(Keypairs[i][0], Keypairs[i][1], Utils.from_base64(requests[0]['data']['x']))
        responses.append({
            "fx": Utils.to_base64(fx), 
            "vk": Utils.to_base64(vk) 
        })
    # Average time taken to evaluate OPRF by a single evaluator
    evaluator_time = (time.perf_counter() - evaluator_time) / len(requests)
    
    # Finish Call ID Generation
    call_id_resume = time.perf_counter()
    call_id = libcpex.create_call_id(responses=responses, masks=masks)
    call_id_time += time.perf_counter() - call_id_resume
    
    # Encrypt and MAC, then sign the requests
    provider_enc_sign_time = time.perf_counter()
    storage_reqs = libcpex.create_storage_requests(call_id=call_id, msg=token)
    provider_enc_sign_time = time.perf_counter() - provider_enc_sign_time
    
    # Message Store operations 
    message_store_pub_time = time.perf_counter()
    for storage_req in storage_reqs:
        gpk = groupsig.get_gpk() 
        req = storage_req['data']
        groupsig.verify(sig=req['sig'], msg=req['idx'] + req['ctx'], gpk=gpk)
        value = req['idx'] + '.' + req['ctx'] + '.' + req['sig']
        cache.cache_for_seconds(req['idx'], value, config.REC_TTL_SECONDS)
    # Average time taken to store a message by a single store
    message_store_pub_time = (time.perf_counter() - message_store_pub_time) / len(storage_reqs)
    
    # Retrieval Protocol
    create_ret_reqs_and_sign = time.perf_counter()
    ret_reqs = libcpex.create_retrieve_requests(call_id=call_id)
    create_ret_reqs_and_sign = time.perf_counter() - create_ret_reqs_and_sign
    
    # Message Store operations for 1 store
    responses = []
    message_store_ret_time = time.perf_counter()
    for ret_req in ret_reqs:
        gpk = groupsig.get_gpk() 
        groupsig.verify(sig=ret_req['data']['sig'], msg=ret_req['data']['idx'], gpk=gpk)
        value = cache.find(ret_req['data']['idx'])
        (msidx, msctx, mssig) = value.split('.')
        responses.append({'idx': msidx, 'ctx': msctx, 'sig': mssig})
    # Average time taken to retrieve a message by a single store
    message_store_ret_time = (time.perf_counter() - message_store_ret_time) / len(ret_reqs)
    
    verify_and_decrypt = time.perf_counter()
    tokens = libcpex.decrypt(call_id=call_id, responses=responses, src=src, dst=dst)
    verify_and_decrypt = time.perf_counter() - verify_and_decrypt
    
    results = [
        ['(1) Call ID Generation', toMs(call_id_time)],
        ['(2) Encrypt and Sign', toMs(provider_enc_sign_time)],
        ['(3) Retrieve Req & Sign', toMs(create_ret_reqs_and_sign)],
        ['(4) Verify and Decrypt', toMs(verify_and_decrypt)],
        ['(5) Server OPRF Eval', toMs(evaluator_time)],
        ['(6) Provider Publish - Refs(1+2)', toMs(call_id_time + provider_enc_sign_time)],
        ['(7) Message Store Publish', toMs(message_store_pub_time)],
        ['(8) Provider Retrieve - Refs(1+3+4)', toMs(call_id_time + create_ret_reqs_and_sign + verify_and_decrypt)],
        ['(9) Message Store Retrieve', toMs(message_store_ret_time)],
    ]
    
    if printResults:
        print("\nMicrobenchmark Results:")
        for result in results:
            print(f"{result[0]}: {result[1]} ms")
        print("\n")
        
    return results
    

async def main():
    results_folder = os.path.dirname(os.path.abspath(__file__)) + '/results'
    files.create_dir_if_not_exists(results_folder)
    resutlsloc = f"{results_folder}/microbench.csv"
    results = [['Operation', 'Runtime (ms)']]
    files.write_csv(resutlsloc, results)
    
    print(f"Running {numIters} iterations of the CPEX protocol microbenchmark...")
    start = time.perf_counter()
    results = []
    with Pool(processes=os.cpu_count()) as pool:
        results = pool.map(benchCpexProtocol, [False] * numIters)
    for result in results:
        files.append_csv(resutlsloc, result)
    end = round(time.perf_counter() - start, 2)
    print(f"Results have been saved to {resutlsloc}. Total time taken: {end} seconds.")

if __name__ == '__main__':
    asyncio.run(main())