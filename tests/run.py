import asyncio, argparse
from cpex.prototype.provider import Provider
from cpex.helpers import dht
from cpex.models import cache
from cpex.crypto import groupsig

dht.set_cache_client(cache.connect())
gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()

async def main(mode: str):
    provider = Provider(
        pid='1', 
        impl=False, 
        mode=mode, 
        cps_url='http://atis-cps-1',
        gsk=gsk,
        gpk=gpk
    )
    signal, token = await provider.originate()
    res = await provider.retrieve(signal)
    assert token == res.Identity

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, help='Mode of execution', required=True)
    args = parser.parse_args()
    asyncio.run(main(args.mode))

    # certs = "-----BEGIN CERTIFICATE-----\nMIIBgDCCASagAwIBAgIUMiWdEjbUVOZnm8rXNYoCs4xYb6wwCgYIKoZIzj0EAwIw\nPzELMAkGA1UEBhMCVVMxEDAOBgNVBAgMB1Zlcm1vbnQxDjAMBgNVBAoMBUlDQSAx\nMQ4wDAYDVQQDDAVpY2FfMTAeFw0yNDEyMjAwNjEwMDdaFw0yNTEyMjAwNjEwMDda\nMEExCzAJBgNVBAYTAlVTMRAwDgYDVQQIDAdWZXJtb250MREwDwYDVQQKDAhPUkcg\nc3BfMTENMAsGA1UEAwwEc3BfMTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABOqf\nOWfKmxJsqIQwT89Tb4Du69VFJ8FUkHEoVot5gEHabuSJT2E6MWUepkhGZUcO4n9Q\nHHmYp9pkxCcFwSQUNnAwCgYIKoZIzj0EAwIDSAAwRQIgNqdB3G9eucUPZiS2UeRc\nxQ4Dv+moruQ6nSFIv7iTAMECIQDzf2nxA8QASc4aIiufI0WXd9tjmkqyX+sBzLL5\nP4eG5Q==\n-----END CERTIFICATE-----\n"
    # print(get_public_key_from_cert(certs))