from cpex.stirshaken.passports import Passport, PassportHeader, PassportPayload
from cpex.helpers import files
from cpex.config import CONF_DIR
from cpex.constants import PRIV_KEY

cps_0: str = 'http://localhost:10000/publish'
x5u: str = f'http://localhost:8888/certs/cps_0'


if __name__ == '__main__':
    keys = files.read_json(fileloc=f"{CONF_DIR}/cps.0.certs.json")
    
    header: PassportHeader = PassportHeader(x5u=x5u)
    payload: PassportPayload = PassportPayload(
        attest='A',
        orig={'tn': '1111111111'},
        dest={'tn': '2222222222'},
    )
    passport: Passport = Passport(header, payload)
    passport.sign(key=keys[PRIV_KEY])
    
    publish_req: Publish = Publish(
        passport=passport, 
        issuer=issuer, 
        cps_base_url=cps_1, 
        x5u=x5u
    )
    publish_req.authenticate(keypath=keypath)
    res = publish_req.submit()
    print('Response\n', res)