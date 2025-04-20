import argparse
import traceback
import asyncio  # <-- Make sure to import asyncio
from jodi.prototype.simulations import networked
from jodi.models import persistence
from jodi import constants

def handle_gen(args):
    print(f"Starting Data Generation...",
          f"Providers = {args.num_providers}",
          f"Deploy rate = {args.deploy_rate}"
    )
    try:
        networked.datagen(
            num_providers=args.num_providers,
            deploy_rate=args.deploy_rate,
            force_clean=args.force_clean
        )
    except Exception as ex:
        print("> Error:", ex)

async def handle_run(args):
    try:
        if args.call_path:
            await networked.simulate_call({
                'mode': args.mode,
                'route': networked.get_route_from_bitstring(args.call_path)
            })
        else:
            print("Simulating pending routes...")
            networked.run()
        print("SIMULATION COMPLETED")
    except Exception as ex:
        print("An error occurred:", ex)
        traceback.print_exc()

def handle_cleanup(args):
    print("Cleaning up resources...", end='')
    networked.cleanup()
    print("DONE")


if __name__ == '__main__':
    # Create the main parser
    parser = argparse.ArgumentParser(description="Running Jodi Experiments")
    parser.add_argument("--mode", help="Mode of operation", default=constants.MODE_JODI, choices=constants.MODES)

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands: gen, run, clean")

    # Subparser for `gen`
    parser_gen = subparsers.add_parser('gen', help="Generate configuration")
    parser_gen.add_argument("-n", "--num-providers",
                            help="Number of providers in the network",
                            required=True, type=int)
    parser_gen.add_argument("-r", "--deploy-rate",
                            help="STIR/SHAKEN deployment rate in percentage. Default=14",
                            default=14, type=float)
    parser_gen.add_argument('-f', "--force-clean",
                            action="store_true", default=False,
                            help="Force clean existing records")
    parser_gen.set_defaults(func=handle_gen)

    # Subparser for `run`
    parser_run = subparsers.add_parser('run', help="Run the experiment")
    parser_run.add_argument("-c", "--call-path", required=False,
                            help="Parameter for the experiment")
    parser_run.set_defaults(func=handle_run)

    # Subparser for `clean`
    parser_clean = subparsers.add_parser('clean', help="Clean up resources")
    parser_clean.add_argument('-f', "--force-clean",
                              action="store_true", default=False,
                              help="Force clean existing records")
    parser_clean.set_defaults(func=handle_cleanup)

    # Parse the arguments
    args = parser.parse_args()

    # Dispatch to the appropriate function
    if args.command:
        # If the chosen sub-command’s function is a coroutine, run it with asyncio
        if asyncio.iscoroutinefunction(args.func):
            asyncio.run(args.func(args))
        else:
            args.func(args)
    else:
        parser.print_help()
