from cpex.helpers import http
import asyncio, time, json, aiohttp
from cpex import config

proto = 'oobss'

def main():
    eloop = asyncio.new_event_loop()
    asyncio.set_event_loop(eloop)
    http.set_session(http.create_session(event_loop=eloop))
        
    src, dst = '11111111111', '22222222222'
    pub_res = eloop.run_until_complete(http.posts([
        {
            'url': f'http://{proto}-proxy/publish',
            'data': {'src': src, 'dst': dst, 'passport': 'header.payload.signature'},
        }
    ]))
    
    print(pub_res)
    # time.sleep(3)
    ret_res = eloop.run_until_complete(http.get(f'http://{proto}-proxy/retrieve/{src}/{dst}'))
    print(ret_res)
    
    http.destroy_session()
    eloop.close()

if __name__ == '__main__':
    main()