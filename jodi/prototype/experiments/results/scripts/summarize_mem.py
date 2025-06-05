import pandas as pd
import re

from jodi import config

input_file = 'jodi/prototype/experiments/results/resource-exp/docker_stats.csv'
output_file = 'jodi/prototype/experiments/results/resource-exp/docker_stats_summary.csv'

def parse_memusage(memusage):
    # Extract float value before 'MiB'
    match = re.match(r'([\d.]+)\s*MiB', str(memusage))
    return float(match.group(1)) if match else 0.0

# Read the CSV
df = pd.read_csv(input_file)

# Clean MemUsage to float (in MiB)
df['MemUsage'] = df['MemUsage'].apply(parse_memusage)

# Group and aggregate: only get max memory usage
summary = df.groupby('Name').agg(
    max_mem_usage=('MemUsage', 'max')
).reset_index()

# Save to CSV
summary.to_csv(output_file, index=False)

print(f"Summary written to {output_file}")
print(summary.to_string(index=False))
