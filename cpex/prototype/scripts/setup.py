from argparse import ArgumentParser
from cpex.crypto import groupsig
from cpex.helpers import files
import cpex.config as config
import yaml
from pylibcpex import Utils
from collections import defaultdict

def groupsig_setup():
    if config.TGS_GPK and config.TGS_GSK and config.TGS_GML and config.TGS_MSK:
        return
    
    msk, gpk, gml, gsk = groupsig.setup()
    files.update_env_file('.env', {
        'TGS_MSK': msk,
        'TGS_GPK': gpk,
        'TGS_GML': gml,
        'TGS_GSK': gsk
    })
    
    print("Group signature setup completed")

def get_node_hosts():
    hosts_file = 'automation/hosts.yml'
    nodes = defaultdict(list)

    with open(hosts_file, 'r') as file:
        data = yaml.safe_load(file)
        if not data or 'all' not in data or 'hosts' not in data['all']:
            raise Exception("Invalid hosts.yml format")
        
        for i, name in enumerate(data['all']['hosts'].keys()):
            ip_addr = data['all']['hosts'][name]['ansible_host']

            ev_name = config.get_container_prefix('cpex') + f'ev-{i}'
            nodes['cpex-ev'].append({
                'id': Utils.hash256(ev_name.encode()).hex(), 
                'name': ev_name, 
                'fqdn': f'{ip_addr}:10431',
                'ip': ip_addr,
                'url': f'http://{ip_addr}:10431'
            })

            ms_name = config.get_container_prefix('cpex') + f'ms-{i}'
            nodes['cpex-ms'].append({
                'id': Utils.hash256(ms_name.encode()).hex(), 
                'name': ms_name, 
                'fqdn': f'{ip_addr}:10432', 
                'ip': ip_addr,
                'url': f'http://{ip_addr}:10432'
            })

            cps_name = config.get_container_prefix('atis') + f'cps-{i}'
            nodes['sti-cps'].append({
                'id': Utils.hash256(cps_name.encode()).hex(), 
                'name': cps_name, 
                'fqdn': f'{ip_addr}:11432', 
                'ip': ip_addr,
                'url': f'http://{ip_addr}:11432'
            })

    return nodes

def main(args):
    if args.all or args.groupsig:
        groupsig_setup()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--groupsig', action='store_true', help='Setup group signature')
    parser.add_argument('--all', action='store_true', help='Setup everything')
    args = parser.parse_args()
    # if no arguments, print help
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)