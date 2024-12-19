from argparse import ArgumentParser
from cpex.crypto import groupsig
from cpex.helpers import files

def groupsig_setup():
    msk, gpk, gml, gsk = groupsig.setup()
    files.update_env_file('.env', {
        'TGS_MSK': msk,
        'TGS_GPK': gpk,
        'TGS_GML': gml,
        'TGS_GSK': gsk
    })

def main():
    groupsig_setup()

if __name__ == '__main__':
    main()