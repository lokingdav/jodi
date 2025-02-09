import asyncio, argparse, json
from cpex.prototype.provider import Provider
from cpex.helpers import dht
from cpex.models import cache
from cpex.crypto import groupsig
from cpex.helpers import logging
from cpex.prototype.simulations.networked import NetworkedSimulator

mode = 'cpex'
cps_id = 1
fqdn1 = '54.211.175.148:10433'# f'atis-cps-{cps_id}'
fqdn2 = '54.211.175.148:10434'# f'atis-cps-{cps_id}'

cache.set_client(cache.connect())
gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()

async def main():
    sim = NetworkedSimulator()
    sim.create_nodes()

    logger = logging.create_logger('tests/run.py')

    provider1 = Provider({
        'pid': 'P0',
        'impl': False,
        'mode': mode,
        'gsk': gsk,
        'gpk': gpk,
        'n_ev': 1,
        'n_ms': 1,
        'logger': logger,
        'next_prov': (1, 0),
        'cps': { 'url': f'http://{fqdn1}', 'fqdn': fqdn1 },
        'cr': {'x5u': f'http://{fqdn1}/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
    })

    signal, token = await provider1.originate()

    provider2 = Provider({
        'pid': 'P1',
        'impl': False,
        'mode': mode,
        'gsk': gsk,
        'gpk': gpk,
        'n_ev': 1,
        'n_ms': 1,
        'logger': logger,
        'next_prov': None,
        'cps': { 'url': f'http://{fqdn2}', 'fqdn': fqdn2 },
        'cr': {'x5u': f'http://{fqdn2}/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
    })
    token_retrieved = await provider2.terminate(signal)

    # print(f'\nSignal: {signal}')
    # print(f'Original Token: {token}')
    # print(f'Retrieved Token: {token_retrieved}\n')
    print(f"Tokens Match: {token == token_retrieved}")
    print(f'Total Latency: {provider1.get_latency_ms() + provider2.get_latency_ms()} ms')


    logging.print_logs(logger)

if __name__ == '__main__':
    asyncio.run(main())
