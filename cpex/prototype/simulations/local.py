from cpex.prototype.simulations.networked import NetworkedSimulator
from cpex.prototype.simulations.entities import Provider
from cpex.models import cache
from cpex.crypto import groupsig
from pylibcpex import Utils
from cpex import config
import json, threading, time, random
import numpy as np

cache_client = None
gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()

def set_cache_client(client):
    global cache_client
    cache_client = client

class LocalSimulator(NetworkedSimulator):
    def __init__(self):
        super().__init__()

    def create_provider_instance(self, pid, impl, mode, options, next_prov):
        return Provider(params=self.create_prov_params(
            pid=pid, 
            impl=impl, 
            mode=mode, 
            options=options, 
            next_prov=next_prov
        ), cache_client=cache_client)
    
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

def get_status(ntype: str):
    p = config.EV_AVAILABILITY if ntype == 'ev' else config.MS_AVAILABILITY
    weights = [p, 1 - p]
    return bool(np.random.choice([True, False], p=weights))

def get_uptime():
    return time.time() + config.UP_TIME_DURATION

def get_downtime(ntype: str):
    secs = config.EV_DOWN_TIME if ntype == 'ev' else config.UP_TIME_DURATION
    return time.time() + secs

def format_time(seconds):
    return time.strftime("%H:%M:%S", time.gmtime(seconds))

def simulate_churn(ntype, nodes):
    down_count, up_count = 0, 0
    for i in range(len(nodes)):
        avail = nodes[i].get('avail')
        if avail and avail['until'] > time.time():
            if avail['up']:
                up_count += 1
            else:
                down_count += 1
            continue
        is_up = get_status(ntype)
        nodes[i]['avail'] = {
            'up': is_up,
            'until': get_uptime() if is_up else get_downtime(ntype=ntype)
        }
        if is_up:
            up_count += 1
        else:
            down_count += 1
    return nodes, {'up_count': up_count, 'down_count': down_count}

def wait_a_while(stop_churn: threading.Event):
    for _ in range(config.MAX_UPTIME_SECONDS):
        time.sleep(1)
        if stop_churn.is_set():
            return

def network_churn(stop_churn: threading.Event):   
    evals = cache.find(client=cache_client, key=config.EVALS_KEY, dtype=dict)
    stores = cache.find(client=cache_client, key=config.STORES_KEY, dtype=dict)
        
    while not stop_churn.is_set():
        time.sleep(config.CHURN_INTERVAL_SECONDS)
        if 0 < config.EV_AVAILABILITY < 1:
            evals, status = simulate_churn('ev', evals)
            # print(f"EVs - Up: {status['up_count']}, Down: {status['down_count']}")
            cache.save(client=cache_client, key=config.EVALS_KEY, value=json.dumps(evals))
        
        if 0 < config.MS_AVAILABILITY < 1:
            stores, status = simulate_churn('ms', stores)
            # print(f"MSs - Up: {status['up_count']}, Down: {status['down_count']}\n")
            cache.save(client=cache_client, key=config.STORES_KEY, value=json.dumps(stores))