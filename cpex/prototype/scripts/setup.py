from argparse import ArgumentParser
from cpex.crypto import groupsig
from cpex.helpers import files

def groupsig_setup():
    msk, gpk, gml, gsk = groupsig.setup()
    files.update_env_file('.env', {
        'GS_MSK': msk,
        'GS_GPK': gpk,
        'GS_GML': gml,
        'GS_GSK': gsk
    })

def main():
    groupsig_setup()

if __name__ == '__main__':
    main()