from cpex.models import cache
from pylibcpex import Utils
from cpex.crypto.oprf import KeyRotation
from cpex.crypto import libcpex
from cpex.helpers import http
import asyncio

cache.set_client(cache.connect())
gsk, gpk = libcpex.groupsig.get_gsk(), libcpex.groupsig.get_gpk()

async def main():
    call_details = libcpex.normalize_call_details('1234567890', '0987654321')
    i_k = libcpex.get_index_from_call_details(call_details)
    x, mask = libcpex.Oprf.blind(call_details)
    x_str = Utils.to_base64(x)
    sig = libcpex.groupsig.sign(msg=str(i_k) + x_str, gsk=gsk, gpk=gpk)

    response = await http.posts(reqs=[
        {
            'url': 'http://evaluator/evaluate',
            'data': { 'i_k': i_k, 'x': x_str, 'sig': sig }
        }
    ])

    print(response)

    cid = libcpex.Oprf.unblind(
        Utils.from_base64(response[0]['fx']), 
        Utils.from_base64(response[0]['vk']), 
        mask
    )

    print(f"Call ID: {Utils.to_base64(cid)}")


if __name__ == '__main__':
    asyncio.run(main())