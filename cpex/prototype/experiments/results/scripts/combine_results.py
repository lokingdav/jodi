import os, json, argparse
from cpex.helpers import files
import pandas as pd

def combine_k6():
    folder = 'cpex/prototype/experiments/results/k6'
    filenames = os.listdir(folder)
    rows = []
    dp = 3
    
    for file in filenames:
        if file.endswith('.json'):
            with open(f'{folder}/{file}', 'r') as f:
                data = json.load(f)
                (prot, _) = file.split('-')
                rows.append([
                    prot, # Protocol
                    data['metrics']['vus']['max'], # VUs
                    round(data['metrics']['http_req_duration']['min'], dp), # Min
                    round(data['metrics']['http_req_duration']['max'], dp), # Max
                    round(data['metrics']['http_req_duration']['med'], dp), # Median
                    round(data['metrics']['http_req_duration']['avg'], dp), # Avg
                    round(data['metrics']['http_req_duration']['p(90)'], dp), # p90
                    round(data['metrics']['http_req_duration']['p(95)'], dp), # p95
                    round(data['metrics']['iterations']['rate'], dp), # Calls/s
                    round(data['metrics']['http_reqs']['rate'], dp), # Requests/s
                    round(data['metrics']['http_req_failed']['value'], 5) # Requests Failed
                ])

    rows.sort(key=lambda x: (x[1], x[0]))
    rows = [['Protocol', 'VUs', 'Min', 'Max', 'Median', 'Avg', 'P(90)', 'P(95)', 'Calls/s', 'Requests/s', 'Requests Failed']] + rows
    files.write_csv('cpex/prototype/experiments/results/k6.csv', rows)
    
def combine_lat():
    folder = 'cpex/prototype/experiments/results'
    filenames = ['experiment-3a.csv', 'experiment-3b.csv']
    output_file = os.path.join(folder, 'experiment-3.csv')  # Output file
    dp = 3  # Decimal places for rounding

    # Read and combine CSV files
    dataframes = []
    for filename in filenames:
        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):  # Ensure the file exists
            df = pd.read_csv(file_path)
            dataframes.append(df)
        else:
            print(f"Warning: {file_path} not found.")

    # Merge data if we have files
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)

        # Round numeric columns to specified decimal places
        combined_df = combined_df.round(dp)

        # Save combined results
        combined_df.to_csv(output_file, index=False)
        print(f"Combined results saved to {output_file}")
    else:
        print("No valid files found. Nothing to combine.")



def main(args):
    if args.type == 'k6':
        combine_k6()
    elif args.type == 'lat':
        combine_lat()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Combine results from multiple files into a CSV file.')
    parser.add_argument('--type', type=str, choices=['k6', 'lat'], required=True, help='load or latency')
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)