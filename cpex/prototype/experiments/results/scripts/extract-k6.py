import os, json
from cpex.helpers import files

folder = 'cpex/prototype/experiments/results/k6'

def main():
    filenames = os.listdir(folder)
    rows = []
    dp = 3
    for file in filenames:
        if file.endswith('.json'):
            with open(f'{folder}/{file}', 'r') as f:
                data = json.load(f)
                (prot, _) = file.split('-')
                rows.append([
                    prot, 
                    data['metrics']['vus']['max'], 
                    round(data['metrics']['http_req_duration']['med'], dp),
                    round(data['metrics']['iterations']['rate'], dp),
                ])

    rows.sort(key=lambda x: (x[1], x[0]))
    rows = [['Protocol', 'VUs', 'Median']] + rows
    files.write_csv('cpex/prototype/experiments/results/k6.csv', rows)

if __name__ == '__main__':
    main()