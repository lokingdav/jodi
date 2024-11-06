import argparse
from cpex.providers import simulation
from cpex.models import persistence

def handle_gen(args):
    print(f"Starting Data Generation...", 
          f"Providers = {args.num_providers}", 
          f"Deploy rate = {args.deploy_rate}"
    )
    try:
        simulation.datagen(
            num_providers=args.num_providers,
            deploy_rate=args.deploy_rate,
            force_clean=args.force_clean
        )
    except Exception as ex:
        print("> Error: ", ex)

def handle_run(args):
    print(f"Running with args:", args.call_path)

def handle_clean(args):
    if persistence.has_pending_routes():
        print("Pending call routes exists. Rerun this command with -f to force cleaning")
        return
    
    print("Cleaning up resources...", end='')
    simulation.clean()
    print("DONE")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Running CPeX Experiments")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands: gen, run, clean")

    parser_gen = subparsers.add_parser('gen', help="Generate configuration")
    parser_gen.add_argument("-n", "--num-providers", help="Number of providers in the network", required=True, type=int)
    parser_gen.add_argument("-r", "--deploy-rate", help="STIR/SHAKEN deployment rate in percentage. Default=14", default=14, type=float)
    parser_gen.add_argument('-f', "--force-clean", action="store_true", default=False, help="Force clean existing records")
    parser_gen.set_defaults(func=handle_gen)

    parser_run = subparsers.add_parser('run', help="Run the experiment")
    parser_run.add_argument("-c", "--call-path", type=int, required=False, help="Parameter a for the experiment")
    parser_run.set_defaults(func=handle_run)

    parser_clean = subparsers.add_parser('clean', help="Clean up resources")
    parser_clean.set_defaults(func=handle_clean)

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()
