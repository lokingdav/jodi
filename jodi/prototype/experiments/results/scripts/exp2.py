from jodi.prototype.experiments.results.scripts import helpers
import numpy as np

oob_frac = 0.788
total_call_rate = 23_148
median_call_rate = 1_000
file_path = "jodi/prototype/experiments/results/experiment-2.csv"
columns = ['PUB:P', 'PUB:EV', 'PUB:MS', 'RET:P', 'RET:EV', 'RET:MS']
stats = helpers.compute_stoobsstics(file_path, columns)
n_mad, N, M = 3, 20, 20

oob_calls_rate = total_call_rate * oob_frac
p_rate = median_call_rate * oob_frac

stats = helpers.estimate_vcpus(
    stats=stats,
    n_mad=n_mad, 
    call_rate=oob_calls_rate, 
    p_rate=p_rate,
    N=N, 
    M=M
)

# helpers.estimate_bandwidth(
#     call_rate=oob_calls_rate, 
#     p_rate=p_rate,
#     N=N, 
#     M=M
# )
helpers.estimate_storage(call_rate=oob_calls_rate)

