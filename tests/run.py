import asyncio, argparse, json, random, time
from jodi.prototype.provider import Provider
from jodi.helpers import dht
from jodi.models import cache
from jodi.crypto import groupsig, billing
from jodi.helpers import mylogging, http, files
from jodi.prototype.simulations.networked import NetworkedSimulator
from jodi import config
from itertools import product


cache.set_client(cache.connect())
jodi_conf = {'n_ev': 3, 'n_ms': 3, 'gsk': groupsig.get_gsk(), 'gpk': groupsig.get_gpk()}
credentials = files.read_json(fileloc="conf/certs.json")

async def main(args):
    http.set_session(http.create_session())
    
    sim = NetworkedSimulator()
    sim.create_nodes()
    cpss = cache.find(config.CPS_KEY, dtype=dict)
    crs = cache.find(config.CR_KEY, dtype=dict)
    
    if cpss:
        [cps1, cps2] = cpss[0:2]
    else:
        cps1 = {'url': 'http://example1.com', 'fqdn': 'example1.com'}
        cps2 = {'url': 'http://example2.com', 'fqdn': 'example2.com'}
        
    if crs:
        [cr1, cr2] = crs[0:2]
    else:
        cr1 = {'url': 'http://cr1.com', 'fqdn': 'cr1.com'}
        cr2 = {'url': 'http://cr2.com', 'fqdn': 'cr2.com'}

    logger = mylogging.create_stream_logger('tests/run.py')

    mode = args.mode

    provider1 = Provider({
        'pid': 'P0',
        'impl': False,
        'mode': mode,
        'logger': logger,
        'next_prov': (1, 0),
        'bt': billing.create_endorsed_token(config.VOPRF_SK),
        'cps': { 'url': cps1['url'], 'fqdn': cps1['fqdn'] },
        'cr': {'x5u': cr1['url'] + f'/certs/ocrt-1', 'sk': credentials['ocrt-1']['sk']},
        **jodi_conf,
    })

    signal, token = await provider1.originate()

    provider2 = Provider({
        'pid': 'P1',
        'impl': False,
        'mode': mode,
        'logger': logger,
        'next_prov': None,
        'bt': billing.create_endorsed_token(config.VOPRF_SK),
        'cps': { 'url': cps2['url'], 'fqdn': cps2['fqdn'] },
        'cr': {'x5u': cr2['url'] + f'/certs/ocrt-2', 'sk': credentials['ocrt-2']['sk']},
        **jodi_conf,
    })
    token_retrieved = await provider2.terminate(signal)

    print(f"Tokens Match: {token == token_retrieved}")
    print(f'Total Latency: {provider1.get_latency_ms() + provider2.get_latency_ms()} ms')

    mylogging.print_logs(logger)
    
    await http.async_destroy_session()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode', type=str, default='jodi', help='Mode to run the simulation in')
    args = parser.parse_args()
    asyncio.run(main(args))
    