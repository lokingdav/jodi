import asyncio, argparse, json
from cpex.prototype.provider import Provider
from cpex.helpers import dht
from cpex.models import cache
from cpex.crypto import groupsig

mode = 'atis'
cps_id = 1
fqdn1 = '54.211.175.148:10433'# f'atis-cps-{cps_id}'
fqdn2 = '54.211.175.148:10434'# f'atis-cps-{cps_id}'


async def main():
    provider1 = Provider({
        'pid': 'P0',
        'impl': False,
        'mode': mode,
        'gsk': None,
        'gpk': None,
        'n_ev': 1,
        'n_ms': 1,
        'next_prov': None,
        'cps': { 'url': f'http://{fqdn1}', 'fqdn': fqdn1 },
        'cr': {'x5u': f'http://{fqdn1}/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
    })

    signal, token = await provider1.originate()

    provider2 = Provider({
        'pid': 'P1',
        'impl': False,
        'mode': mode,
        'gsk': None,
        'gpk': None,
        'n_ev': 1,
        'n_ms': 1,
        'next_prov': None,
        'cps': { 'url': f'http://{fqdn2}', 'fqdn': fqdn2 },
        'cr': {'x5u': f'http://{fqdn2}/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
    })
    print('signal:', signal)
    print('Original Token:', token)

    token_retrieved = await provider2.terminate(signal)
    print('Retrieved Token:', token_retrieved)
    print("\nTokens Match:", token == token_retrieved)
    print('done')
    # print(token)

if __name__ == '__main__':
    asyncio.run(main())
