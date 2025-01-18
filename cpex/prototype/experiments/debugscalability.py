from cpex.prototype import compose
from cpex.helpers import dht
from cpex.models import cache
import traceback

from cpex.prototype.simulations import networked

route = {"_id": 19, "status": "pending", "route": [[0,0], [3,0],[33,0], [20,0]], "mode": "cpex", "log": False}

def main():
    compose.set_cache_client(cache.connect())
    compose.cache_repositories(mode='cpex')
    networked.init_worker()
    runs = 1000
    for i in range(1, runs+1):
        route['_id'] = i
        try:
            networked.simulate_call_sync(route)
        except Exception as e:
            print(f"Error on run {i}: {e}")
            traceback.print_exc()
        print(f"Completed {i}/{runs} runs")

if __name__ == "__main__":
    main()