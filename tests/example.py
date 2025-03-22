from cpex.helpers import http
import asyncio, time, json
from cpex.crypto import billing
from cpex import config

async def main():
    token = billing.create_endorsed_token(sk=config.VOPRF_SK)
    print("Token:", token)
    verified = billing.verify_token(vk=config.VOPRF_VK, token=token)
    print("Verified:", verified)

if __name__ == '__main__':
    asyncio.run(main())