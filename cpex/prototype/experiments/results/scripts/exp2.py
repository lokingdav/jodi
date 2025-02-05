from cpex.prototype.experiments.results.scripts import helpers
import numpy as np


if __name__ == "__main__":
    # print(helpers.get_oob_fraction())
    oob_frac = 0.788
    total_call_rate = 23_148
    file_path = "cpex/prototype/experiments/results/experiment-2.csv"
    columns = ['PUB:P', 'PUB:EV', 'PUB:MS', 'RET:P', 'RET:MS']
    stats = helpers.compute_statistics(file_path, columns)
    n_mad, n_ev, n_ms = 2, 20, 20
    
    oob_calls_rate = 23_148 * oob_frac
    stats = helpers.estimate_vcpus(
        stats=stats,
        n_mad=n_mad, 
        rate=oob_calls_rate, 
        p_rate=500*oob_frac,
        n_ev=n_ev, 
        n_ms=n_ms
    )
    print(stats)