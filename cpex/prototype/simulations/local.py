from cpex.prototype.simulations.networked import NetworkedSimulator
from cpex.prototype.simulations.entities import Provider
from cpex.models import cache
from cpex.crypto import groupsig
from pylibcpex import Utils
from cpex import config
import json

cache_client = None
gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()

def set_cache_client(client):
    global cache_client
    cache_client = client

class LocalSimulator(NetworkedSimulator):
    def __init__(self):
        super().__init__()

    def create_provider_instance(self, pid, impl, mode, options):
        return Provider(
            pid=pid, 
            impl=bool(int(impl)),
            mode=mode,
            log=options.get('log', True),
            gsk=gsk,
            gpk=gpk,
            cache_client=cache_client,
            n_ev= options.get('n_ev'),
            n_ms= options.get('n_ms')
        )
    
    def create_nodes(self, mode: str, num_evs: int, num_repos: int):
        evals, stores = [], []
        cclient = cache.connect()

        for i in range(num_repos):
            name = f'cpex-node-ms-{i}'
            stores.append({
                'id': Utils.hash256(name.encode('utf-8')).hex(),
                'name': name,
                'fqdn': name,
                'url': f'http://{name}'
            })
        if stores:
            cache.save(client=cclient, key=config.STORES_KEY, value=json.dumps(stores))

        for i in range(num_evs):
            name = f'cpex-node-ev-{i}'
            evals.append({
                'id': Utils.hash256(name.encode('utf-8')).hex(),
                'name': name,
                'fqdn': name,
                'url': f'http://{name}'
            })
        if evals:
            cache.save(client=cclient, key=config.EVALS_KEY, value=json.dumps(evals))
    