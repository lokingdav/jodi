import time, os, asyncio, json
from cpex.helpers import misc, http, files, dht
from cpex.crypto import libcpex, groupsig
from pylibcpex import Oprf, Utils
from cpex import config, constants
from cpex.models import cache
from multiprocessing import Pool


numIters = 100
gpk = groupsig.get_gpk()
gsk = groupsig.get_gsk()

evals = []
stores = []

cache_client = None

# Sample src, dst and JWT token
src = '16841333538'
dst = '16847000540'
token = "eyJhbGciOiJFUzI1NiIsInBwdCI6InNoYWtlbiIsInR5cCI6InBhc3Nwb3J0IiwieDV1IjoiaHR0cDovL2NlcnQtcmVwby9jZXJ0cy9zcF8xIn0.eyJpYXQiOjE3MzQ4OTU2NjMsImF0dGVzdCI6IkMiLCJvcmlnIjp7InRuIjpbIjE2ODQxMzMzNTM4Il19LCJkZXN0Ijp7InRuIjpbIjE2ODQ3MDAwNTQwIl19fQ.7xC7RuEnCAp62ZSvmtWsZ3Hco-bvT9EU-JoFk48HzINCh4GLaDTR8o7S042TrB5cWK6kCwSMjddoiH5JUExB3g"

def toMs(seconds):
    return round(seconds * 1000, 3)

def init_worker():
    global cache_client
    cache_client = cache.connect()
    dht.set_cache_client(cache_client)

def cid_generation(Keypairs):
    start_client_part_1 = time.perf_counter()
    call_details = libcpex.normalize_call_details(src=src, dst=src)
    requests, masks = libcpex.create_evaluation_requests(call_details, gsk=gsk, gpk=gpk)
    client_part_1_time = time.perf_counter() - start_client_part_1

    assert len(requests) == config.OPRF_EV_PARAM, f"Expected {config.OPRF_EV_PARAM} requests, got {len(requests)}"
    
    responses = []
    start_server_part = time.perf_counter()
    for i, req in enumerate(requests):
        assert groupsig.verify(req['data']['sig'], str(req['data']['i_k']) + req['data']['x'], gpk=gpk)
        (fx, vk) = Oprf.evaluate(Keypairs[i][0], Keypairs[i][1], Utils.from_base64(req['data']['x']))
        responses.append({
            "fx": Utils.to_base64(fx), 
            "vk": Utils.to_base64(vk) 
        })
    server_time = (time.perf_counter() - start_server_part) / len(requests)

    assert len(responses) == config.OPRF_EV_PARAM, f"Expected {config.OPRF_EV_PARAM} responses, got {len(responses)}"
    
    start_client_part_2 = time.perf_counter()
    call_id = libcpex.create_call_id(responses=responses, masks=masks)
    client_part_2_time = time.perf_counter() - start_client_part_2

    client_time = client_part_1_time + client_part_2_time
    
    return {
        'call_id': call_id,
        'client_time': client_time,
        'server_time': server_time,
        'total_time': client_time + server_time
    }

def benchCpexProtocol(options):
    global cache_client

    print(f"Running with {options['num_ev']} EVs and {options['num_ms']} MSs")

    config.OPRF_EV_PARAM = options['num_ev']
    config.REPLICATION = options['num_ms']

    Keypairs = [Oprf.keygen() for _ in range(config.OPRF_EV_PARAM)]
        
    cidgen1 = cid_generation(Keypairs)
    
    # Encrypt and MAC, then sign the requests
    provider_enc_sign_time = time.perf_counter()
    storage_reqs = libcpex.create_storage_requests(call_id=cidgen1['call_id'], msg=token, gsk=gsk, gpk=gpk)
    provider_enc_sign_time = time.perf_counter() - provider_enc_sign_time
    
    # Message Store operations 
    message_store_pub_time = time.perf_counter()
    for storage_req in storage_reqs:
        req = storage_req['data']
        assert groupsig.verify(sig=req['sig'], msg=req['idx'] + req['ctx'], gpk=gpk)
        value = req['idx'] + '.' + req['ctx'] + '.' + req['sig']
        cache.cache_for_seconds(
            client=cache_client, 
            key=req['idx'], 
            value=value, 
            seconds=config.REC_TTL_SECONDS
        )
    # Average time taken to store a message by a single store
    message_store_pub_time = (time.perf_counter() - message_store_pub_time) / len(storage_reqs)
    
    # Retrieval Protocol
    create_ret_reqs_and_sign = time.perf_counter()
    ret_reqs = libcpex.create_retrieve_requests(call_id=cidgen1['call_id'], gsk=gsk, gpk=gpk)
    create_ret_reqs_and_sign = time.perf_counter() - create_ret_reqs_and_sign
    
    # Message Store operations for 1 store
    responses = []
    message_store_ret_time = time.perf_counter()
    for ret_req in ret_reqs:
        assert groupsig.verify(sig=ret_req['data']['sig'], msg=ret_req['data']['idx'], gpk=gpk)
        value = cache.find(
            client=cache_client, 
            key=ret_req['data']['idx']
        )
        (msidx, msctx, mssig) = value.split('.')
        responses.append({'idx': msidx, 'ctx': msctx, 'sig': mssig})
    # Average time taken to retrieve a message by a single store
    message_store_ret_time = (time.perf_counter() - message_store_ret_time) / len(ret_reqs)
    
    verify_and_decrypt = time.perf_counter()
    dec_token = libcpex.decrypt(call_id=cidgen1['call_id'], responses=responses, src=src, dst=dst, gpk=gpk)
    verify_and_decrypt = time.perf_counter() - verify_and_decrypt
    
    assert dec_token == token, "Decrypted token does not match original token"
    
    results = [
        config.OPRF_EV_PARAM, 
        config.REPLICATION,
        toMs(cidgen1['client_time'] + provider_enc_sign_time), # provider publish
        toMs(cidgen1['server_time']), # oprf server evaluate
        toMs(message_store_pub_time), # message store publish
        toMs(cidgen1['client_time'] + create_ret_reqs_and_sign + verify_and_decrypt), 
        toMs(message_store_ret_time),
        toMs(
            cidgen1['total_time'] * 2 # includes provider and server for publish and retrieve
            + provider_enc_sign_time # provider publish
            + create_ret_reqs_and_sign # create retrieve requests
            + verify_and_decrypt # verify and decrypt
        )
    ]
    
    return results
    
def create_nodes():
    global evals, stores
    evals, stores = [], []

    for i in range(30):
        name = f'cpex-node-ms-{i}'
        stores.append({
            'id': Utils.hash256(name.encode('utf-8')).hex(),
            'name': name,
            'fqdn': name,
            'url': f'http://{name}'
        })
        name = f'cpex-node-ev-{i}'
        evals.append({
            'id': Utils.hash256(name.encode('utf-8')).hex(),
            'name': name,
            'fqdn': name,
            'url': f'http://{name}'
        })

async def main():
    create_nodes()
    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/microbench.csv"
    files.write_csv(resutlsloc, [['Num Evals', 'Num Stores', 'PUB:P', 'PUB:EV', 'PUB:MS', 'RET:P', 'RET:MS', 'Latency']])
    
    print(f"Running {numIters} iterations of the CPEX protocol microbenchmark...")
    start = time.perf_counter()
    params = []


        # print(f"Iteration {_+1}/{numIters}")
    with Pool(processes=os.cpu_count(), initializer=init_worker) as pool:
        count = 10
        for _ in range(numIters):
            for n_ev in range(1, count+1):
                for n_ms in range(1, count+1):
                    params.append({'num_ms': n_ms, 'num_ev': n_ev})
        results = pool.map(benchCpexProtocol, params)
        files.append_csv(resutlsloc, results)

    end = round(time.perf_counter() - start, 2)
    print(f"Results have been saved to {resutlsloc}.\nTotal time taken: {end} seconds.")

if __name__ == '__main__':
    asyncio.run(main())