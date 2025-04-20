import os, json, argparse
from jodi.helpers import files
import pandas as pd

oobss = 'oob-s/s'
jodi = 'jodi'

def combine_k6(prefix):
    folder = 'jodi/prototype/experiments/results/k6'
    filenames = os.listdir(folder)
    rows = []
    dp = 3
    
    for file in filenames:
        if file.startswith(prefix) and file.endswith('.json'):
            with open(f'{folder}/{file}', 'r') as f:
                data = json.load(f)
                (proto, _) = file.split('-')

                if 'jodi' in proto:
                    proto = jodi
                else:
                    proto = oobss

                row = [proto, data['metrics']['vus']['max']]

                if prefix == 'rt':
                    row.append(round(data['metrics']['http_req_duration']['min'], dp))
                    row.append(round(data['metrics']['http_req_duration']['max'], dp))
                    row.append(round(data['metrics']['http_req_duration']['med'], dp))
                    row.append(round(data['metrics']['http_req_duration']['avg'], dp))
                    row.append(round(data['metrics']['http_req_duration']['p(90)'], dp))
                    row.append(round(data['metrics']['http_req_duration']['p(95)'], dp))
                elif prefix == 'sr':
                    row.append(data['metrics']['iterations']['count'])
                    row.append(data['metrics']['successful_calls']['count'] if 'successful_calls' in data['metrics'] else 0)

                if 'successful_calls' in data['metrics']:
                    success_rate = round(data['metrics']['successful_calls']['count']/data['metrics']['iterations']['count']*100, dp)
                else:
                    success_rate = 0
                    
                row.append(success_rate)

                rows.append(row)

    rows.sort(key=lambda x: (x[1], x[0]))

    header = ['Protocol', 'VUs']
    if prefix == 'rt':
        header += ['Min', 'Max', 'Median', 'Avg', 'P(90)', 'P(95)']
    if prefix == 'sr':
        header += ['Calls-Sent', 'Calls-Processed']
        
    header.append('Success-Rate')

    rows = [header] + rows
    filename = f'jodi/prototype/experiments/results/k6-{prefix}.csv'
    files.write_csv(filename, rows)
    print(f'Combined results saved to {filename}')
    
def combine_lat():
    folder = 'jodi/prototype/experiments/results'
    filenames = ['experiment-3b.csv', 'experiment-3a.csv']
    output_file = os.path.join(folder, 'experiment-3.csv')  # Output file
    dp = 3  # Decimal places for rounding

    # Read and combine CSV files
    dataframes = []
    for filename in filenames:
        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):  # Ensure the file exists
            df = pd.read_csv(file_path)
            # modify the protocol column changed oobss to oobss and jodi to jodi
            df['protocol'] = df['protocol'].apply(lambda x: oobss if x == 'oobss' else jodi)
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
    if args.type == 'rt':
        combine_k6(prefix='rt')
    if args.type == 'sr':
        combine_k6(prefix='sr')
    elif args.type == 'lat':
        combine_lat()
    elif args.type == 'all':
        combine_k6(prefix='rt')
        combine_k6(prefix='sr')
        combine_lat()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Combine results from multiple files into a CSV file.')
    parser.add_argument('--type', type=str, choices=['sr', 'rt', 'lat', 'all'], required=True, help='load or latency')
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)