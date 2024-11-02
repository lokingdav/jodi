import argparse
from cpex.helpers import compose
from multiprocessing import Pool
import traceback

processes=4

def create_node(cps_id: str):
    print('Creating CPS with ID:', cps_id)
    try:
        compose.add_cps_node(cps_id=cps_id)
    except:
        print("An error happened")
        traceback.print_exc()
        pass
    
def main(initial_cps_nodes):
    start_id = 1
    with Pool(processes=processes) as pool:
        ids = list(range(start_id, initial_cps_nodes + start_id))
        pool.map(create_node, ids)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Add initial CPS nodes.")
    parser.add_argument(
        "--initial-cps-nodes", 
        type=int, 
        default=1,  # Default value as in the original script
        help="The number of initial CPS nodes to add"
    )
    args = parser.parse_args()
    
    main(args.initial_cps_nodes)
