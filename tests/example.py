from cpex.helpers import http
import asyncio, time, json

loads = json.load(open('conf/loads.json'))

async def main():
    load = loads[0]
    req = {
        'url': load['atis']['pub_url'],
        'data': {'passports': [load['passport']]},
        'headers': {'Authorization': 'Bearer ' + load['atis']['pub_bearer']}
    }
    res = await http.posts([req])
    print(res)

if __name__ == '__main__':
    asyncio.run(main())