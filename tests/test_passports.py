from cpex.stirshaken.passports import Passport, PassportHeader, PassportPayload
from cpex.actions.cps_reqs_handler import Publish

issuer: str = 'sp1'
keypath = f'certs/{issuer}/key.pem'
cps_1: str = 'http://localhost:7771/passports'
x5u: str = f'http://ca:80/certs/{issuer}.cert'

if __name__ == '__main__':
    header: PassportHeader = PassportHeader(x5u=x5u)
    payload: PassportPayload = PassportPayload(
        attest='A',
        orig={'tn': '1111111111'},
        dest={'tn': '2222222222'},
    )
    passport: Passport = Passport(header, payload)
    passport.sign(keypath=keypath)
    publish_req: Publish = Publish(
        passport=passport, 
        issuer=issuer, 
        cps_base_url=cps_1, 
        x5u=x5u
    )
    publish_req.authenticate(keypath=keypath)
    res = publish_req.submit()
    print('Response\n', res)
    