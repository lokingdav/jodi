from pygroupsig import groupsig, constants, signature, memkey, grpkey, mgrkey, gml as GML
from cpex import config

SCHEME = constants.BBS04_CODE

def setup():
    bbs04 = groupsig.setup(SCHEME)
    gsk = mgr_generate_member_keys(bbs04['mgrkey'], bbs04['grpkey'], bbs04['gml'])
    
    msk = mgrkey.mgrkey_export(bbs04['mgrkey'])
    gpk = grpkey.grpkey_export(bbs04['grpkey'])
    gml = GML.gml_export(bbs04['gml'])
    
    return msk, gpk, gml, gsk

def mgr_import_keys():
    groupsig.init(SCHEME, 0)
    return {
        'msk': mgrkey.mgrkey_import(SCHEME, config.GS_MSK),
        'gpk': grpkey.grpkey_import(SCHEME, config.GS_GPK),
        'gml': GML.gml_import(SCHEME, config.GS_GML)
    }

def mgr_generate_member_keys(msk, gpk, gml):
    groupsig.init(SCHEME, 0)
    if (type(msk) == str):
        msk = mgrkey.mgrkey_import(SCHEME, msk)
    if (type(gpk) == str):
        gpk = grpkey.grpkey_import(SCHEME, gpk)
    if (type(gml) == str):
        gml = GML.gml_import(SCHEME, gml)
        
    msg1 = groupsig.join_mgr(0, msk, gpk, gml=gml)
    msg2 = groupsig.join_mem(1, gpk, msgin = msg1)
    usk = msg2['memkey']
    
    return memkey.memkey_export(usk)
        
def get_gpk():
    groupsig.init(SCHEME, 0)
    if not config.GS_GPK:
        raise Exception('GPK not set')
    return grpkey.grpkey_import(SCHEME, config.GS_GPK)
    
def sign(msg: str, gsk: str, gpk: str) -> str:
    groupsig.init(SCHEME, 0)
    sigma = groupsig.sign(msg, gsk, gpk)
    return signature.signature_export(sigma)

def verify(sig: str, msg: str, gpk: str):
    sig = signature.signature_import(SCHEME, sig)
    return groupsig.verify(sig, msg, gpk)

def import_signing_key(gsk: str) -> dict:
    groupsig.init(SCHEME, 0)
    return memkey.memkey_import(SCHEME, gsk)