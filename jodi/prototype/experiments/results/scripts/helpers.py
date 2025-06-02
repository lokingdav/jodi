import pandas as pd
import math
import networkx as nx
import numpy as np
from jodi.prototype import network
from jodi import config

from scipy.stats import median_abs_deviation

def compute_stoobsstics(file_path, columns):
    """
    Read a CSV, filter to given columns, and return a DataFrame with
    min, max, median, MAD for each column.
    """
    df = pd.read_csv(file_path)
    # Strip whitespace from column names just to be safe
    df.columns = df.columns.str.strip()
    
    # Filter to only the specified columns
    df_filtered = df[columns]

    # Compute summary stoobsstics
    # .describe() returns many stats; we'll keep only min/max for illustration
    summary_stats = df_filtered.describe().T[['min', 'max']]

    # Add median
    summary_stats['median'] = df_filtered.median()

    # Correct MAD computation
    summary_stats['MAD'] = df_filtered.apply(median_abs_deviation)

    return summary_stats

def estimate_vcpus(stats, n_mad, call_rate, p_rate, N, M):
    stats['compute'] = stats['median'] + n_mad * stats['MAD']  # in ms

    processing_time_per_record = stats['compute'] / 1000.0

    stats['vCPUs'] = processing_time_per_record * call_rate

    stats.loc['PUB:P', 'vCPUs'] = processing_time_per_record['PUB:P'] * p_rate
    stats.loc['RET:P', 'vCPUs'] = processing_time_per_record['RET:P'] * p_rate

    stats.loc['PUB:EV', 'vCPUs'] = stats.loc['PUB:EV', 'vCPUs'] / N
    stats.loc['RET:EV', 'vCPUs'] = stats.loc['RET:EV', 'vCPUs'] / N
        
    stats.loc['PUB:MS', 'vCPUs'] = stats.loc['PUB:MS', 'vCPUs'] / M
    stats.loc['RET:MS', 'vCPUs'] = stats.loc['RET:MS', 'vCPUs'] / M
    
    print(stats)
    
    res = {
        'Provider': math.ceil(stats.loc['PUB:P', 'vCPUs'] + stats.loc['RET:P', 'vCPUs']),
        'Evaluator': math.ceil(stats.loc['PUB:EV', 'vCPUs'] + stats.loc['RET:EV', 'vCPUs']),
        'Message Store': math.ceil(stats.loc['PUB:MS', 'vCPUs'] + stats.loc['RET:MS', 'vCPUs']),
    }
    print('\nVCPUs\n------------------')
    for k in res:
        print(f"{k}:\t{res[k]}")
    print('\n')
    return res

def get_oob_call_rate(call_rate, n=7300, total_subs=300_000_000, oob_frac=0.4243):
    graph = nx.barabasi_albert_graph(n=n, m=2)
    degrees = np.array([degree for node, degree in graph.degree()])
    total_degree = degrees.sum()
    degrees = degrees / total_degree
    subscribers = total_subs * degrees
    
    possible_calls = total_subs * (total_subs - 1)
    same_provider_calls = np.sum(subscribers * (subscribers - 1))
    cross_provider_fraction = (possible_calls - same_provider_calls) / possible_calls
    
    print(f"\nCross Provider Fraction:\t{cross_provider_fraction}")
    oob_call_rate = math.ceil((cross_provider_fraction * call_rate) * oob_frac)
    
    print(f"\nCall Rate:\t{call_rate} per sec")
    print(f"OOB calls:\t{oob_call_rate} per sec")
    
    return oob_call_rate

def get_oob_fraction():
    x_vals = [20, 40, 80, 100, 160]
    y_vals = []
    for x in x_vals:
        for i in range(10):
            # print(f"Running for {x} providers")
            routes, stats = network.create(
                num_providers=x, 
                deploy_rate=config.SS_DEPLOY_RATE
            )
            y_vals.append(routes[0]['total'] / routes[0]['all'])
    
    y_vals = np.array(y_vals)
    # print('Mean', np.mean(y_vals))
    # print('Std', np.std(y_vals))
    print('Median', np.median(y_vals))
    print('MAD', np.median(np.abs(y_vals - np.median(y_vals))))
    # print('Max', np.max(y_vals))
    # print('Min', np.min(y_vals))
    return np.median(y_vals)

def estimate_storage(call_rate, N = 20, M = 20):
    # Storage Requirement
    # Token: 2 * 0.078 billion per day * 300 Bytes * 1 day
    # EV == Token
    # MS: Token + (2 * 0.078 billion per day * 1024 Bytes * 15 seconds)
    print("Call rate:", call_rate)
    token_size = 300
    aggregation_cycle_in_secs = 60
    cache_duration_in_secs = 15
    ctx_size = 1024
    
    ev_req_per_sec = 2 * call_rate / N
    ms_req_per_sec = 2 * call_rate / M
    
    print("MS Req per sec:", ms_req_per_sec)
    print("EV Req per sec:", ev_req_per_sec)
    
    ev_storage = ev_req_per_sec * aggregation_cycle_in_secs * token_size
    ms_storage = (ms_req_per_sec * aggregation_cycle_in_secs * token_size) + (ms_req_per_sec * cache_duration_in_secs * ctx_size)
    
    gb = 1024 * 1024 * 1024
    # Convert to GB
    ev_storage = math.ceil(ev_storage / gb)
    ms_storage = math.ceil(ms_storage / gb)
    
    print(f"Storage Requirement\n------------------")
    print(f"Evaluator: {ev_storage} GB")
    print(f"Message Store: {ms_storage} GB")
    

def estimate_bandwidth(call_rate, p_rate, N, M):
    # Bandwidth For 
    # provider: (6 * 1000 per second) * 1.5 * (2000 Bytes) to megabits per second
    # message store: (2 * 0.078 billion per day) * 1.5 * (2000 Bytes) to megabits per second
    # Evaluator: (2 * 0.078 billion per day) * 1.5 * (900 Bytes) to megabits per second
    ev_req_per_sec = 2 * call_rate / N
    ms_req_per_sec = 2 * call_rate / M
    