import time
from cpex.helpers import misc, http, files
from cpex.crypto import libcpex, groupsig
from pylibcpex import Oprf, Utils
from cpex import config
from cpex.models import persistence

numIters = 1000

# Sample src, dst and JWT token
src = '16841333538'
dst = '16847000540'
token = "eyJhbGciOiJFUzI1NiIsInBwdCI6InNoYWtlbiIsInR5cCI6InBhc3Nwb3J0IiwieDV1IjoiaHR0cDovL2NlcnQtcmVwby9jZXJ0cy9zcF8xIn0.eyJpYXQiOjE3MzQ4OTU2NjMsImF0dGVzdCI6IkMiLCJvcmlnIjp7InRuIjpbIjE2ODQxMzMzNTM4Il19LCJkZXN0Ijp7InRuIjpbIjE2ODQ3MDAwNTQwIl19fQ.7xC7RuEnCAp62ZSvmtWsZ3Hco-bvT9EU-JoFk48HzINCh4GLaDTR8o7S042TrB5cWK6kCwSMjddoiH5JUExB3g"
# OPRF keys for server 1 and server 2
(sk1, pk1) = Oprf.keygen()
(sk2, pk2) = Oprf.keygen()

def benchProviderAndServerPublish():
    message_stores = persistence.get_repositories()
    
    pp1st = time.perf_counter()
    call_details = libcpex.get_call_details(src=src, dst=src)
    requests, scalars = libcpex.create_evaluation_requests(call_details)
    pp1et = time.perf_counter()
    
    responses = []
    server_begin_time = time.perf_counter()
    groupsig.verify(requests[0]['data']['sig'], str(requests[0]['data']['idx']) + requests[0]['data']['x'], config.TGS_GPK)
    (fx1, vk1) = Oprf.evaluate(sk1, pk1, Utils.from_base64(requests[0]['data']['x']))
    responses.append({ "fx": Utils.to_base64(fx1), "vk": Utils.to_base64(vk1) })
    server_end_time = time.perf_counter()
    
    groupsig.verify(requests[1]['data']['sig'], str(requests[1]['data']['idx']) + requests[1]['data']['x'], config.TGS_GPK)
    (fx2, vk2) = Oprf.evaluate(sk2, pk2, Utils.from_base64(requests[1]['data']['x']))
    responses.append({ "fx": Utils.to_base64(fx2), "vk": Utils.to_base64(vk2) })
    
    pp2st = time.perf_counter()
    call_id = libcpex.create_call_id(s1res=responses[0], s2res=responses[1], scalars=scalars)
    # Encrypt and MAC, then sign the requests
    ctx = libcpex.encrypt_and_mac(call_id=call_id, plaintext=token)
    reqs = libcpex.create_storage_requests(
        call_id=call_id, 
        ctx=ctx,
        nodes=message_stores[:],
        count=config.REPLICATION, 
    )
    pp2et = time.perf_counter()
    
    providerTime = (pp1et - pp1st) + (pp2et - pp2st)
    serverTime = server_end_time - server_begin_time
    print(f"Provider Time: {providerTime * 1000} ms")
    print(f"Server Time: {serverTime * 1000} ms")

def main():
    benchProviderAndServerPublish()

if __name__ == '__main__':
    main()