from argparse import ArgumentParser
from cpex.crypto import groupsig, libcpex
from cpex.helpers import files, misc, dht
from cpex import config, constants
import yaml, re, random
from pylibcpex import Utils, Oprf
from collections import defaultdict
from cpex.prototype.stirshaken import stirsetup, verify_service, auth_service, certs

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
    return stirsetup.setup()

def setup_sample_loads(certs=None):
    if not certs:
        certs = setup_certificates()
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
    num_loads = config.LOAD_TEST_COUNT
    attests = ['A', 'B', 'C']
    nodes = get_node_hosts()

    if not nodes[config.CPS_KEY]:
        raise Exception("No CPS nodes found")
    
    num_certs = config.NO_OF_INTERMEDIATE_CAS * config.NUM_CREDS_PER_ICA
    loads = []
    progress = 1
    for cps in nodes[config.CPS_KEY]:
        for i in range(num_loads):
            print(f"Creating load {progress}/{num_loads * len(nodes[config.CPS_KEY])}")
            progress += 1
            p_ocrt = certs[f"{constants.OTHER_CREDS_KEY}-{random.randint(0, num_certs - 1)}"]
            iss = f'P{random.randint(0, 1000)}'
            authService = auth_service.AuthService(
                ownerId=iss,
                private_key_pem=p_ocrt['sk'],
                x5u=f"{nodes[config.CPS_KEY][random.randint(0, len(nodes[config.CPS_KEY]) - 1)]['url']}/certs/{p_ocrt['id']}",
            )
            orig, dest, attest = misc.fake_number(), misc.fake_number(), random.choice(attests)
            rand_cps = nodes[config.CPS_KEY][random.randint(0, len(nodes[config.CPS_KEY]) - 1)]
            data = {'orig': orig, 'dest': dest}
            data['passport'] = authService.create_passport(orig=orig, dest=dest, attest=attest)
            # data['x5u'] = authService.x5u
            data['atis'] = {
                'pub_url': f"{cps['url']}/publish/{dest}/{orig}",
                'pub_name': cps['fqdn'],
                'pub_bearer': authService.authenticate_request(
                    action='publish',
                    orig=orig,
                    dest=dest,
                    passports=[data['passport']],
                    iss=iss,
                    aud=cps['fqdn']
                ),
                'ret_url': f"{rand_cps['url']}/retrieve/{dest}/{orig}",
                'ret_name': rand_cps['fqdn'],
                'ret_bearer': authService.authenticate_request(
                    action='retrieve',
                    orig=orig,
                    dest=dest,
                    passports=[],
                    iss=iss,
                    aud=rand_cps['fqdn']
                )
            }

            calldetails = libcpex.normalize_call_details(src=orig, dst=dest)
            x, mask = Oprf.blind(calldetails)
            x = Utils.to_base64(x)
            i_k = libcpex.get_index_from_call_details(calldetails)
            
            cid = Utils.random_bytes(32)
            idx = Utils.to_base64(Utils.hash256(cid))
            ctx = libcpex.encrypt_and_mac(call_id=cid, plaintext=data['passport'])

            mss, evs = [], []
            if nodes[config.STORES_KEY]:
                mss = dht.get_stores(keys=cid, count=config.n_ms, nodes=nodes[config.STORES_KEY])
                mss = [ms['url'] for ms in mss]
            if nodes[config.EVALS_KEY]:
                evs = dht.get_evals(keys=cid, count=config.n_ev, nodes=nodes[config.EVALS_KEY])
                evs = [ev['url'] for ev in evs]

            data['cpex'] = {
                'idx': idx, 
                'ctx': ctx, 
                'oprf': {
                    'x': x, 
                    'i_k': i_k, 
                    'sig': groupsig.sign(msg=str(i_k)+x, gsk=gsk, gpk=gpk)
                },
                'pub_sig': groupsig.sign(msg=idx + ctx, gsk=gsk, gpk=gpk),
                'ret_sig': groupsig.sign(msg=idx, gsk=gsk, gpk=gpk),
                'mss': mss,
                'evs': evs
            }
            loads.append(data)
    random.shuffle(loads)
    files.override_json(config.CONF_DIR + '/loads.json', loads)
    
def main(args):
    if args.all or args.groupsig:
        groupsig_setup()
        setup_certificates()
    else:
        if args.groupsig:
            groupsig_setup()
        elif args.certs:
            setup_certificates()
        elif args.loads:
            setup_sample_loads()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--groupsig', action='store_true', help='Setup group signature')
    parser.add_argument('--certs', action='store_true', help='Setup STIR/SHAKEN certificates')
    parser.add_argument('--loads', action='store_true', help='Setup sample loads')
    parser.add_argument('--all', action='store_true', help='Setup everything')
    args = parser.parse_args()
    # if no arguments, print help
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)