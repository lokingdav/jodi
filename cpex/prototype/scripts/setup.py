from argparse import ArgumentParser
from cpex.crypto import groupsig
from cpex.helpers import files
import cpex.config as config
import yaml, re
from pylibcpex import Utils
from collections import defaultdict
from cpex.prototype.stirshaken import stirsetup

def groupsig_setup():
    if config.TGS_GPK and config.TGS_GSK and config.TGS_GML and config.TGS_MSK:
        return update_vars_file(config.TGS_GPK)
    
    msk, gpk, gml, gsk = groupsig.setup()
    files.update_env_file('.env', {
        'TGS_MSK': msk,
        'TGS_GPK': gpk,
        'TGS_GML': gml,
        'TGS_GSK': gsk
    })

    update_vars_file(gpk)
    
    print("Group signature setup completed")

def update_vars_file(gpk):
    try:
        # 1. Read existing data
        with open('automation/playbooks/vars.yml', 'r') as varsFile:
            data = yaml.safe_load(varsFile)
            if data is None:
                data = {}  # Handle empty file gracefully
                
        # 2. Update data
        data['tgs_gpk_value'] = gpk

        # 3. Write updated data
        with open('automation/playbooks/vars.yml', 'w') as varsFile:
            yaml.dump(data, varsFile)

    except Exception as e:
        raise Exception("Failed to update vars.yml") from e

def is_valid_ipv4(ip):
    pattern = r"^(25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)$"
    return re.match(pattern, ip) is not None

def create_node(fqdn):
    return {'id': Utils.hash256(fqdn.encode()).hex(), 'name': fqdn, 'fqdn': fqdn, 'ip': fqdn, 'url': f'http://{fqdn}'}

def get_node_hosts():
    hosts_file = 'automation/hosts.yml'
    nodes = defaultdict(list)

    if files.is_empty(hosts_file):
        return nodes
    
    with open(hosts_file, 'r') as file:
        data = yaml.safe_load(file)
        if not data or 'all' not in data or 'hosts' not in data['all']:
            raise Exception("Invalid hosts.yml format")
        
        for i, name in enumerate(data['all']['hosts'].keys()):
            ip_addr = data['all']['hosts'][name]['ansible_host']
            
            if is_valid_ipv4(ip_addr):
                nodes[config.EVALS_KEY].append(create_node(f'{ip_addr}:{config.EV_PORT}'))
                nodes[config.STORES_KEY].append(create_node(f'{ip_addr}:{config.MS_PORT}'))
                nodes[config.CPS_KEY].append(create_node(f'{ip_addr}:{config.CPS_PORT}'))
                nodes[config.CPS_KEY].append(create_node(f'{ip_addr}:{str(int(config.CPS_PORT) + 1)}'))
            else:
                node = create_node(ip_addr)
                if '-ev-' in ip_addr or 'evaluator' in ip_addr:
                    nodes[config.EVALS_KEY].append(node)
                elif '-ms-' in ip_addr or 'message-store' in ip_addr:
                    nodes[config.STORES_KEY].append(node)
                elif '-cps-' in ip_addr:
                    nodes[config.CPS_KEY].append(node)
    return nodes

def setup_certificates():
    stirsetup.setup()
    
def main(args):
    if args.all or args.groupsig:
        groupsig_setup()
        setup_certificates()
    else:
        if args.groupsig:
            groupsig_setup()
        elif args.certs:
            setup_certificates()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--groupsig', action='store_true', help='Setup group signature')
    parser.add_argument('--certs', action='store_true', help='Setup STIR/SHAKEN certificates')
    parser.add_argument('--all', action='store_true', help='Setup everything')
    args = parser.parse_args()
    # if no arguments, print help
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)