from cpex.prototype import compose
from cpex.helpers import dht
from cpex.models import cache
import traceback, time, datetime
from cpex.crypto import libcpex

from cpex.prototype.simulations import local, networked

route = {'_id': 140, 'status': 'pending', 'route': [[9, 0], [2, 1], [11, 0], [15, 0]], 'mode': 'cpex'}

def setup():
    cache_client = cache.connect()
    compose.set_cache_client(cache_client)
    local.set_cache_client(cache_client)
    dht.set_cache_client(cache_client)
    networked.init_worker()
    
    
def simulate():
    setup()
    runs = 1
    Simulator = local.LocalSimulator()
    for i in range(1, runs+1):
        route['_id'] = i
        try:
            Simulator.simulate_call_sync(route)
        except Exception as e:
            print(f"Error on run {i}: {e}")
            traceback.print_exc()
        print(f"Completed {i}/{runs} runs")

def trychurn():
    nodes = [
        {'id': '1', 'name': 'node1', 'fqdn': 'node1', 'url': 'http://node1'},
        {'id': '2', 'name': 'node2', 'fqdn': 'node2', 'url': 'http://node2'},
    ]
    for i in range(100):
        time.sleep(1)
        print("time: ", datetime.datetime.now())
        nodes = local.simulate_churn(nodes)
        
if __name__ == "__main__":
    trychurn()