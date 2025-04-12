from argparse import ArgumentParser
from cpex.crypto import groupsig, libcpex, billing
from cpex.helpers import files, misc, dht
from cpex import config, constants
import yaml, re, random
from pylibcpex import Utils, Oprf, Voprf
from collections import defaultdict
from cpex.prototype.stirshaken import stirsetup, auth_service

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
    
def voprt_setup():
    if config.VOPRF_SK and config.VOPRF_VK:
        return
    sk, vk = Voprf.keygen()
    files.update_env_file('.env', {
        'VOPRF_SK': Utils.to_base64(sk),
        'VOPRF_VK': Utils.to_base64(vk)
    })

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
                
                nodes[config.CR_KEY].append(create_node(f'{ip_addr}:{config.CR_PORT}'))
                
                nodes[config.CPS_KEY].append(create_node(f'{ip_addr}:{config.CPS_0_PORT}'))
                # nodes[config.CPS_KEY].append(create_node(f'{ip_addr}:{config.CPS_1_PORT}'))
            else:
                node = create_node(ip_addr)
                if '-ev-' in ip_addr or 'evaluator' in ip_addr:
                    nodes[config.EVALS_KEY].append(node)
                elif '-ms-' in ip_addr or 'message-store' in ip_addr:
                    nodes[config.STORES_KEY].append(node)
                elif '-cps-' in ip_addr:
                    nodes[config.CPS_KEY].append(node)
                elif '-cr' in ip_addr:
                    nodes[config.CR_KEY].append(node)
    return nodes

def setup_certificates():
    return stirsetup.setup()

def setup_sample_loads(creds=None):
    if not creds:
        creds = setup_certificates()
        
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
    attests = ['A', 'B', 'C']
    nodes = get_node_hosts()

    if not nodes[config.CPS_KEY]:
        raise Exception("No CPS nodes found")
    
    num_certs = config.NO_OF_INTERMEDIATE_CAS * config.NUM_CREDS_PER_ICA
    loads = []
    
    for i in range(num_certs):
        print(f"Creating load {i+1}/{num_certs}")
        ck = f"{constants.OTHER_CREDS_KEY}-{i}"
        iss = f'P{random.randint(0, 1000)}'
        
        cr = nodes[config.CR_KEY][i % len(nodes[config.CR_KEY])]
        pub_cps = nodes[config.CPS_KEY][i % len(nodes[config.CPS_KEY])]
        
        authService = auth_service.AuthService(
            ownerId=iss,
            private_key_pem=creds[ck]['sk'],
            x5u=f"{cr['url']}/certs/{creds[ck]['id']}",
        )
        
        orig, dest, attest = misc.fake_number(), misc.fake_number(), random.choice(attests)
        data = {
            'orig': orig, 
            'dest': dest, 
            'x5u': authService.x5u,
            'passport': authService.create_passport(orig=orig, dest=dest, attest=attest)
        }
        
        data['atis'] = {
            'pub_url': f"{pub_cps['url']}/publish/{dest}/{orig}",
            'pub_name': pub_cps['fqdn'],
            'pub_bearer': authService.authenticate_request(
                action='publish',
                orig=orig,
                dest=dest,
                passports=[data['passport']],
                iss=iss,
                aud=pub_cps['fqdn']
            )
        }

        rets = random.choices(nodes[config.CPS_KEY], k=3)
        data['atis']['rets'] = [] 
        for ret_cps in rets:
            bearer = authService.authenticate_request(
                action='retrieve',
                orig=orig,
                dest=dest,
                passports=[],
                iss=iss,
                aud=ret_cps['fqdn']
            )
            data['atis']['rets'].append({
                'name': ret_cps['fqdn'],
                'url': f"{ret_cps['url']}/retrieve/{dest}/{orig}",
                'bearer': bearer
            })

        calldetails = libcpex.normalize_call_details(src=orig, dst=dest)
        x, mask = Oprf.blind(calldetails)
        x = Utils.to_base64(x)
        i_k = libcpex.get_index_from_call_details(calldetails)
        
        cid = Utils.random_bytes(32)
        idx = Utils.to_base64(Utils.hash256(cid))
        ctx = libcpex.encrypt_and_mac(call_id=cid, plaintext=data['passport'])

        mss, evs = [], []
        mss_peers, evs_peers = "", ""

        if nodes[config.STORES_KEY]:
            mss = dht.get_stores(keys=cid, count=config.n_ms, nodes=nodes[config.STORES_KEY])
            mss_peers = libcpex.get_peers(mss)
            mss = [ms['url'] for ms in mss]

        if nodes[config.EVALS_KEY]:
            evs = dht.get_evals(keys=cid, count=config.n_ev, nodes=nodes[config.EVALS_KEY])
            evs_peers = libcpex.get_peers(evs)
            evs = [ev['url'] for ev in evs]
        
        billable_tk = billing.create_endorsed_token(config.VOPRF_SK)

        pp_eval = Utils.to_base64(Utils.hash256(bytes(str(i_k) + x, 'utf-8')))
        pp_pub = Utils.to_base64(Utils.hash256(bytes(idx + ctx, 'utf-8')))
        pp_ret = Utils.to_base64(Utils.hash256(bytes(idx, 'utf-8')))

        bb_mss = billing.get_billing_hash(billable_tk, mss_peers)
        bb_evs = billing.get_billing_hash(billable_tk, evs_peers)

        data['cpex'] = {
            'idx': idx, 
            'ctx': ctx, 
            'oprf': {
                'x': x, 
                'i_k': i_k,
                'sig': groupsig.sign(msg=pp_eval + bb_evs, gsk=gsk, gpk=gpk)
            },
            'pub_sig': groupsig.sign(msg=pp_pub + bb_mss, gsk=gsk, gpk=gpk),
            'ret_sig': groupsig.sign(msg=pp_ret + bb_mss, gsk=gsk, gpk=gpk),
            'bt': billable_tk,
            'mss': mss,
            'evs': evs,
            'evs_peers': evs_peers,
            'mss_peers': mss_peers
        }
        loads.append(data)
    files.override_json(config.CONF_DIR + '/loads.json', loads)
    
def main(args):
    if args.all or args.groupsig:
        voprt_setup()
        groupsig_setup()
        setup_certificates()
    else:
        if args.groupsig:
            groupsig_setup()
        elif args.certs:
            setup_certificates()
        elif args.loads:
            setup_sample_loads()
        elif args.voprf:
            voprt_setup()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--groupsig', action='store_true', help='Setup group signature')
    parser.add_argument('--voprf', action='store_true', help='Setup VOPRF')
    parser.add_argument('--certs', action='store_true', help='Setup STIR/SHAKEN certificates')
    parser.add_argument('--loads', action='store_true', help='Setup sample loads')
    parser.add_argument('--all', action='store_true', help='Setup everything')
    args = parser.parse_args()
    # if no arguments, print help
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)