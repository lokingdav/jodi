from argparse import ArgumentParser
from cpex.crypto import groupsig
from cpex.helpers import files
import cpex.config as config
import cpex.models.persistence as persistence

def groupsig_setup():
    if config.TGS_GPK and config.TGS_GSK and config.TGS_GML and config.TGS_MSK:
        print("Group signature already setup")
        return
    
    msk, gpk, gml, gsk = groupsig.setup()
    files.update_env_file('.env', {
        'TGS_MSK': msk,
        'TGS_GPK': gpk,
        'TGS_GML': gml,
        'TGS_GSK': gsk
    })
    
    print("Group signature setup completed")
    
def repos_setup():
    respos = files.read_json(config.CONF_DIR + '/repositories.json')
    if respos:
        persistence.seed_repositories(respos)
    print("Repositories seeded")

def main(args):
    if args.all or args.groupsig:
        groupsig_setup()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--groupsig', action='store_true', help='Setup group signature')
    parser.add_argument('--repos', action='store_true', help='Seed repositories')
    parser.add_argument('--all', action='store_true', help='Setup everything')
    args = parser.parse_args()
    # if no arguments, print help
    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)