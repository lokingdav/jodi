import asyncio, argparse, json, random, time
from cpex.prototype.provider import Provider
from cpex.helpers import dht
from cpex.models import cache
from cpex.crypto import groupsig
from cpex.helpers import mylogging
from cpex.prototype.simulations.networked import NetworkedSimulator
from cpex import config
from itertools import product


cache.set_client(cache.connect())
cpex_conf = {'n_ev': 2, 'n_ms': 2, 'gsk': groupsig.get_gsk(), 'gpk': groupsig.get_gpk()}

async def main(args):
    sim = NetworkedSimulator()
    sim.create_nodes()
    cpss = cache.find(config.CPS_KEY, dtype=dict)
    if cpss:
        [cps1, cps2] = cpss[0:2]
    else:
        cps1 = {'url': 'http://example1.com', 'fqdn': 'example1.com'}
        cps2 = {'url': 'http://example2.com', 'fqdn': 'example2.com'}

    logger = mylogging.create_stream_logger('tests/run.py')

    mode = args.mode

    provider1 = Provider({
        'pid': 'P0',
        'impl': False,
        'mode': mode,
        'logger': logger,
        'next_prov': (1, 0),
        'cps': { 'url': cps1['url'], 'fqdn': cps1['fqdn'] },
        'cr': {'x5u': cps2['url'] + f'/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
        **cpex_conf,
    })

    signal, token = await provider1.originate()

    provider2 = Provider({
        'pid': 'P1',
        'impl': False,
        'mode': mode,
        'logger': logger,
        'next_prov': None,
        'cps': { 'url': cps2['url'], 'fqdn': cps2['fqdn'] },
        'cr': {'x5u': cps1['url'] + f'/certs/ocrt-164', 'sk': "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgM2RHw7TQdVvbo9pq\n829inltAQ+Ud8qYRYvbrdu2dIeKhRANCAAS3YDPLvKw41B2PV87DUDn04qOtZDFH\nWJS+M2Nqk7eAgWGVbh6T6BQkiMXifXGvBQ1wFNIPRY1rsi330VP8dzPd\n-----END PRIVATE KEY-----\n"},
        **cpex_conf,
    })
    token_retrieved = await provider2.terminate(signal)

    print(f"Tokens Match: {token == token_retrieved}")
    print(f'Total Latency: {provider1.get_latency_ms() + provider2.get_latency_ms()} ms')

    mylogging.print_logs(logger)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode', type=str, default='cpex', help='Mode to run the simulation in')
    args = parser.parse_args()
    asyncio.run(main(args))
    