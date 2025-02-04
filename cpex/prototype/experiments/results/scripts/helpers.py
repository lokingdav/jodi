import pandas as pd
import math

def compute_statistics(file_path, columns):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    df_filtered = df[columns]
    summary_stats = df_filtered.describe().T[['min', 'max', 'mean', 'std']]
    return summary_stats

def estimate_vcpus(stats, n_std, rate, n_ev, n_ms):
    estimated_time = stats['mean'] + n_std * stats['std']
    processing_time_per_record = estimated_time / 1000  # Convert ms to seconds
    stats[f'compute'] = estimated_time
    stats['vCPUs'] = (processing_time_per_record * rate).apply(lambda x: max(1, round(x)))
    stats.loc['PUB:EV', 'vCPUs'] = max(1, math.ceil(stats.loc['PUB:EV', 'vCPUs'] / n_ev))
    stats.loc['PUB:MS', 'vCPUs'] = max(1, math.ceil(stats.loc['PUB:MS', 'vCPUs'] / n_ms))
    stats.loc['RET:MS', 'vCPUs'] = max(1, math.ceil(stats.loc['RET:MS', 'vCPUs'] / n_ms))
    return stats