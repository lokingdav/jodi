import argparse
from cpex.helpers import compose
from multiprocessing import Pool

processes=4

def create_node(id: str):
    print('Creating CPS with ID:', id)
    try:
        compose.add_cps_node(id=id)
    except:
        pass
    
def main(initial_cps_nodes):
    with Pool(processes=processes) as pool:
        ids = list(range(1, initial_cps_nodes + 1))
        pool.map(create_node, ids)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Add initial CPS nodes.")
    parser.add_argument(
        "--initial-cps-nodes", 
        type=int, 
        default=4,  # Default value as in the original script
        help="The number of initial CPS nodes to add"
    )
    args = parser.parse_args()
    
    main(args.initial_cps_nodes)
