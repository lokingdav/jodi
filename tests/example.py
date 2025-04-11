from cpex.helpers import http
import asyncio, time, json
from cpex import config

proto = 'jodi'

async def main():
    src, dst = '11111111111', '22222222222'
    pub_res = await http.posts([
        {
            'url': f'http://{proto}-proxy/publish',
            'data': {'src': src, 'dst': dst, 'passport': 'header.payload.signature'},
        }
    ])
    print(pub_res)
    # time.sleep(3)
    ret_res = await http.get(f'http://{proto}-proxy/retrieve/{src}/{dst}')
    print(ret_res)

if __name__ == '__main__':
    asyncio.run(main())