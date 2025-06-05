import pandas as pd
import numpy as np
from jodi import config

# Configurable parameters
n_mad = 3  # Number of MADs to add

oob_frac = 0.788
total_call_rate_per_sec = 23_148
median_call_rate_per_sec = 1_000
nodes_count = 30

rate = total_call_rate_per_sec * oob_frac / nodes_count

input_file = config.BENCHMARK_LOG_FILE
output_file = config.BENCHMARK_LOG_FILE.replace('.csv', '_summary.csv')

# Read the input CSV
df = pd.read_csv(input_file)

# Group by 'party' and 'task'
grouped = df.groupby(['party', 'task'])['time']

# Compute statistics in milliseconds
summary = grouped.agg(
    min='min',
    max='max',
    mean='mean',
    median='median'
).reset_index()

# Compute MAD in milliseconds
def mad(x):
    med = x.median()
    return (abs(x - med)).median()

summary['MAD'] = grouped.apply(mad).values

# Compute column: median + n_mad * MAD, but in seconds
summary['compute'] = (summary['median'] / 1000) + n_mad * (summary['MAD'] / 1000)

# Estimate vCPU and take ceiling
summary['vCPU_estimate'] = np.ceil(rate * summary['compute']).astype(int)

# Save to a new CSV file
summary.to_csv(output_file, index=False)

print(f"Summary written to {output_file}")

print(summary.to_string(index=False))
