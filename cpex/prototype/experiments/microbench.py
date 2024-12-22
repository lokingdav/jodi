import time, os, asyncio
from cpex.helpers import misc, http, files
from cpex.crypto import libcpex, groupsig
from pylibcpex import Oprf, Utils
from cpex import config
from cpex.models import persistence, cache


numIters = 100


# Sample src, dst and JWT token
src = '16841333538'
dst = '16847000540'
token = "eyJhbGciOiJFUzI1NiIsInBwdCI6InNoYWtlbiIsInR5cCI6InBhc3Nwb3J0IiwieDV1IjoiaHR0cDovL2NlcnQtcmVwby9jZXJ0cy9zcF8xIn0.eyJpYXQiOjE3MzQ4OTU2NjMsImF0dGVzdCI6IkMiLCJvcmlnIjp7InRuIjpbIjE2ODQxMzMzNTM4Il19LCJkZXN0Ijp7InRuIjpbIjE2ODQ3MDAwNTQwIl19fQ.7xC7RuEnCAp62ZSvmtWsZ3Hco-bvT9EU-JoFk48HzINCh4GLaDTR8o7S042TrB5cWK6kCwSMjddoiH5JUExB3g"
# OPRF keys for server 1 and server 2
(sk1, pk1) = Oprf.keygen()
(sk2, pk2) = Oprf.keygen()

def toMs(seconds):
    return round(seconds * 1000, 3)

async def benchCpexProtocol(printResults=True):
    call_id_time = 0
    server_oprf_time = 0
    provider_enc_sign_time = 0
    
    message_stores = persistence.get_repositories()
    
    # Begin Call ID Generation
    call_id_time = time.perf_counter()
    call_details = libcpex.get_call_details(src=src, dst=src)
    requests, scalars = libcpex.create_evaluation_requests(call_details)
    call_id_time = time.perf_counter() - call_id_time
    
    responses = []
    # OPRF Evaluation by Server 1 and Server 2
    server_oprf_time = time.perf_counter()
    gpk = groupsig.get_gpk()
    groupsig.verify(requests[0]['data']['sig'], str(requests[0]['data']['idx']) + requests[0]['data']['x'], gpk=gpk)
    (fx1, vk1) = Oprf.evaluate(sk1, pk1, Utils.from_base64(requests[0]['data']['x']))
    responses.append({ "fx": Utils.to_base64(fx1), "vk": Utils.to_base64(vk1) })
    server_oprf_time = time.perf_counter() - server_oprf_time
    
    groupsig.verify(requests[1]['data']['sig'], str(requests[1]['data']['idx']) + requests[1]['data']['x'], gpk=gpk)
    (fx2, vk2) = Oprf.evaluate(sk2, pk2, Utils.from_base64(requests[1]['data']['x']))
    responses.append({ "fx": Utils.to_base64(fx2), "vk": Utils.to_base64(vk2) })
    
    call_id_resume = time.perf_counter()
    call_id = libcpex.create_call_id(s1res=responses[0], s2res=responses[1], scalars=scalars)
    call_id_time += time.perf_counter() - call_id_resume
    
    # Encrypt and MAC, then sign the requests
    provider_enc_sign_time = time.perf_counter()
    ctx = libcpex.encrypt_and_mac(call_id=call_id, plaintext=token)
    storage_reqs = libcpex.create_storage_requests(
        call_id=call_id, 
        ctx=ctx,
        nodes=message_stores[:],
        count=config.REPLICATION, 
    )
    provider_enc_sign_time = time.perf_counter() - provider_enc_sign_time
    
    # Message Store operations for 1 store
    message_store_pub_time = time.perf_counter()
    req = storage_reqs[0]['data']
    gpk = groupsig.get_gpk() 
    groupsig.verify(sig=req['sig'], msg=req['idx'] + req['ctx'], gpk=gpk)
    value = req['idx'] + '.' + req['ctx'] + '.' + req['sig']
    cache.cache_for_seconds(req['idx'], value, config.REC_TTL_SECONDS)
    message_store_pub_time = time.perf_counter() - message_store_pub_time
    
    # Retrieval Protocol
    create_ret_reqs_and_sign = time.perf_counter()
    ret_reqs = libcpex.create_retrieve_requests(
        call_id=call_id, 
        nodes=message_stores[:], 
        count=config.REPLICATION
    )
    create_ret_reqs_and_sign = time.perf_counter() - create_ret_reqs_and_sign
    
    # Message Store operations for 1 store
    message_store_ret_time = time.perf_counter()
    ret_req = ret_reqs[0]['data']
    gpk = groupsig.get_gpk() 
    groupsig.verify(sig=ret_req['sig'], msg=ret_req['idx'], gpk=gpk)
    value = cache.find(ret_req['idx'])
    (msidx, msctx, mssig) = value.split('.')
    message_store_ret_time = time.perf_counter() - message_store_ret_time
    
    responses = [res['data'] for res in storage_reqs] # Retrieve responses from storage requests
    
    verify_and_decrypt = time.perf_counter()
    tokens = libcpex.decrypt(call_id=call_id, responses=responses, src=src, dst=dst)
    verify_and_decrypt = time.perf_counter() - verify_and_decrypt
    
    results = [
        ['(1) Call ID Generation', toMs(call_id_time)],
        ['(2) Encrypt and Sign', toMs(provider_enc_sign_time)],
        ['(3) Retrieve Req & Sign', toMs(create_ret_reqs_and_sign)],
        ['(4) Verify and Decrypt', toMs(verify_and_decrypt)],
        ['(5) Server OPRF Eval', toMs(server_oprf_time)],
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
    results = await asyncio.gather(*[benchCpexProtocol(printResults=_ == numIters - 1) for _ in range(numIters)])
    for result in results:
        files.append_csv(resutlsloc, result)
    end = round(time.perf_counter() - start, 2)
    print(f"Results have been saved to {resutlsloc}. Total time taken: {end} seconds.")

if __name__ == '__main__':
    asyncio.run(main())