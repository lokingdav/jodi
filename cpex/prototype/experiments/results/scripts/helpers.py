import pandas as pd
import math
import networkx as nx
import numpy as np
from cpex.prototype import network
from cpex import config

from scipy.stats import median_abs_deviation

def compute_statistics(file_path, columns):
    """
    Read a CSV, filter to given columns, and return a DataFrame with
    min, max, median, MAD for each column.
    """
    df = pd.read_csv(file_path)
    # Strip whitespace from column names just to be safe
    df.columns = df.columns.str.strip()
    
    # Filter to only the specified columns
    df_filtered = df[columns]

    # Compute summary statistics
    # .describe() returns many stats; we'll keep only min/max for illustration
    summary_stats = df_filtered.describe().T[['min', 'max']]

    # Add median
    summary_stats['median'] = df_filtered.median()

    # Correct MAD computation
    summary_stats['MAD'] = df_filtered.apply(median_abs_deviation)

    return summary_stats

def estimate_vcpus(stats, n_mad, rate, p_rate, n_ev, n_ms):
    """
    Estimate vCPUs for each row in 'stats' based on:
      - Median + n_mad * MAD
      - An overall rate
      - A special publisher rate (p_rate)
      - Various scaling factors (n_ev, n_ms) for certain rows
    """
    # 1) Compute estimated time as Median + n * MAD
    estimated_time = stats['median'] + n_mad * stats['MAD']  # in ms

    # Convert milliseconds to seconds
    processing_time_per_record = estimated_time / 1000.0

    # Store the computed time in the dataframe
    stats['compute'] = estimated_time

    # 2) Base vCPUs = (processing_time_per_record * rate)
    #    Then round up to at least 1
    stats['vCPUs'] = (processing_time_per_record * rate).apply(lambda x: max(1, round(x)))

    # 3) For PUB:P and RET:P, use p_rate instead of rate
    #    Here we set a single cell to a single value, no need for .apply
    if 'PUB:P' in stats.index:
        stats.loc['PUB:P', 'vCPUs'] = max(
            1,
            round(processing_time_per_record['PUB:P'] * p_rate)
        )
    if 'RET:P' in stats.index:
        stats.loc['RET:P', 'vCPUs'] = max(
            1,
            round(processing_time_per_record['RET:P'] * p_rate)
        )

    # 4) Adjust vCPU estimates for PUB:EV, PUB:MS, RET:MS
    #    Dividing by n_ev/n_ms and rounding up
    if 'PUB:EV' in stats.index:
        stats.loc['PUB:EV', 'vCPUs'] = max(
            1,
            math.ceil(stats.loc['PUB:EV', 'vCPUs'] / n_ev)
        )
    if 'PUB:MS' in stats.index:
        stats.loc['PUB:MS', 'vCPUs'] = max(
            1,
            math.ceil(stats.loc['PUB:MS', 'vCPUs'] / n_ms)
        )
    if 'RET:MS' in stats.index:
        stats.loc['RET:MS', 'vCPUs'] = max(
            1,
            math.ceil(stats.loc['RET:MS', 'vCPUs'] / n_ms)
        )
    
    return {
        'Evaluator': stats.loc['PUB:EV', 'vCPUs'] * 2, # Publish and Retrieve
        'Provider': stats.loc['PUB:P', 'vCPUs'] + stats.loc['RET:P', 'vCPUs'],
        'Message Store': stats.loc['PUB:MS', 'vCPUs'] + stats.loc['RET:MS', 'vCPUs'],
    }

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