import asyncio, argparse, json
from cpex.prototype.provider import Provider
from cpex.helpers import dht
from cpex.models import cache
from cpex.crypto import groupsig

cps_id = 1

async def main():
    provider = Provider({
        'pid': 'P0',
        'impl': False,
        'mode': 'atis',
        'gsk': None,
        'gpk': None,
        'n_ev': 3,
        'n_ms': 3,
        'next_prov': None,
        'cps': { 'url': f'http://atis-cps-{cps_id}', 'fqdn': f'atis-cps-{cps_id}' },
        'cr': {'x5u': f'http://atis-cps-{cps_id}/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
    })

    signal, token = await provider.originate()
    print('done')
    # print(token)

if __name__ == '__main__':
    asyncio.run(main())

# curl -i -X POST \
#      "http://atis-cps-0/publish/test1/test2" \
#      -H "Authorization: Bearer dummy-token" \
#      -H "Content-Type: application/json" \
#      -d '{"passports":["something"]}'