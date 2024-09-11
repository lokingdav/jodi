import argparse
import docker
import sys
import os

def create_network(network_name):
    """Create a Docker network if it doesn't exist."""
    client = docker.from_env()
    networks = client.networks.list(names=[network_name])
    
    if not networks:
        print(f"Creating Docker network: {network_name}")
        client.networks.create(network_name, driver="bridge")
    else:
        print(f"Network {network_name} already exists.")

def run_docker_containers(num_instances, start_port, image, network_name, mode):
    client = docker.from_env()

    # Get the project root directory (assuming it's the current working directory)
    project_root = os.getcwd()

    for i in range(num_instances):
        instance_num = i + 1
        host_port = start_port + i
        node_name = f"cps_{instance_num}"

        print(f"Running instance {instance_num} with NODE_NAME={node_name} on port {host_port}")

        try:
            # Run the Docker container with volume mount and command
            container = client.containers.run(
                image,
                detach=True,
                name=f"cps_{instance_num}",
                ports={f'{host_port}/tcp': 80},  # Map host port to container port (e.g., 80)
                environment={"NODE_NAME": node_name, "NODE_ENV": "development", "MODE": mode},
                network=network_name,  # Connect container to the Docker network
                volumes={project_root: {'bind': '/app', 'mode': 'rw'}},  # Mount project root to /app inside the container
                command="uvicorn server-ca:app --host 0.0.0.0 --port 80 --reload"  # Command to run
            )
            print(f"Started container cps_{instance_num} on port {host_port}")
        except Exception as e:
            print(f"Error running container cps_{instance_num}: {e}")

def stop_docker_containers():
    client = docker.from_env()
    
    # List all running containers
    containers = client.containers.list(filters={"name": "cps_"})
    
    if not containers:
        print("No running containers found with the prefix 'cps_'")
    else:
        for container in containers:
            print(f"Stopping and removing container {container.name}")
            container.stop()
            container.remove()

def main():
    parser = argparse.ArgumentParser(description='Manage multiple Docker containers with NODE_NAME and NODE_ENV settings.')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # 'up' command
    parser_up = subparsers.add_parser('up', help='Start Docker containers')
    parser_up.add_argument('-n', '--num-instances', type=int, required=True, help='Number of Docker instances to run.')
    parser_up.add_argument('-m', '--mode', type=int, required=True, help='Operational mode [0: ATIS, 1: TDM-OOB]')
    parser_up.add_argument('-p', '--start-port', type=int, default=5000, help='Starting port number for the first instance (default: 5000).')
    parser_up.add_argument('-i', '--image', type=str, default='sti-cps', help='Docker image to use for running the containers (default: sti-cps).')
    parser_up.add_argument('--network', type=str, default='cps_network', help='Docker network name (default: cps_network).')
    
    # 'down' command
    parser_down = subparsers.add_parser('down', help='Stop and remove Docker containers')
    
    args = parser.parse_args()
    
    if args.command == 'up':
        # Check if any containers are already running before starting new ones
        client = docker.from_env()
        containers = client.containers.list(filters={"name": "cps_"})
        if containers:
            print("Error: There are already running containers with the prefix 'cps_'. Please stop them first using the 'down' command.")
            sys.exit(1)
        
        # Create the Docker network if it doesn't exist
        create_network(args.network)
        
        # Run the Docker containers
        run_docker_containers(args.num_instances, args.start_port, args.image, args.network, args.mode)
    
    elif args.command == 'down':
        stop_docker_containers()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
