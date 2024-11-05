from argparse import ArgumentParser
from cpex.providers import network

def main(n: int, r: float):
    routes, stats, adopters = network.create(num_providers=n, deploy_rate=r)
    print('num routes:', len(routes))
    print('stats:', stats)
    
    
if __name__ == '__main__':
    parser = ArgumentParser(description="Running CPeX Experiments")
    parser.add_argument("-n", "--num-providers", help="Number of providers in the network", required=True)
    parser.add_argument("-r", "--deploy-rate", help="STIR/SHAKEN deployment rate in percentage. Default=14", default=14)
    args = parser.parse_args()
    
    main(n=int(args.num_providers), r=float(args.deploy_rate))