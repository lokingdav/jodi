from locust import task, FastHttpUser, between
from pylibcpex import Utils, Oprf
from cpex.crypto import groupsig, libcpex
from cpex.helpers import misc, files
import random, gevent
from cpex.models import cache
from cpex.prototype.simulations import local
from cpex import config

size = random.randint(32, 128)
cache.set_client(cache.connect())
local.LocalSimulator.create_cpex_nodes(20, 20)
default_wait_time = between(0.5, 1.5)
loads = files.read_json(config.CONF_DIR + "/loads.json", default=[])

class EV(FastHttpUser):
    wait_time = default_wait_time
    
    def on_start(self):
        gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
        call_details = libcpex.normalize_call_details(
            src=misc.fake_number(), 
            dst=misc.fake_number()
        )
        x, mask = Oprf.blind(call_details)
        self.x = Utils.to_base64(x)
        self.mask = Utils.to_base64(mask)
        self.i_k = libcpex.get_index_from_call_details(call_details)
        self.sig = groupsig.sign(msg=str(self.i_k) + Utils.to_base64(x), gsk=gsk, gpk=gpk)
        
    @task
    def evaluate(self):
        with self.rest("POST", "/evaluate", json={'i_k': self.i_k, 'x': self.x, 'sig': self.sig}) as res:
            if res.js is None:
                pass

class MS(FastHttpUser):
    wait_time = default_wait_time
    
    def on_start(self):
        gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
        self.idx = Utils.to_base64(Utils.random_bytes(32)) 
        self.ctx = Utils.to_base64(Utils.random_bytes(size))
        self.p_sig = groupsig.sign(msg=self.idx + self.ctx, gsk=gsk, gpk=gpk) 
        self.r_sig = groupsig.sign(msg=self.idx, gsk=gsk, gpk=gpk) 
        
    @task
    def publish(self):
        with self.rest("POST", "/publish", json={'idx': self.idx, 'ctx': self.ctx, 'sig': self.p_sig}) as res:
            if res.js is None:
                pass
        
    @task
    def retrieve(self):
        with self.rest("POST", "/retrieve", json={'idx': self.idx, 'sig': self.r_sig}) as res:
            if res.status_code == 404:
                res.success()
            if res.js is None:
                pass
            
class P(FastHttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.src = misc.fake_number()
        self.dst = misc.fake_number()
        
    @task
    def publish(self):
        with self.rest("POST", "/publish", json={
            'src': self.src, 
            'dst': self.dst, 
            'passport': Utils.to_base64(Utils.random_bytes(size))
        }) as res:
            if res.js is None:
                pass
        
    @task
    def retrieve(self):
        with self.rest("GET", "/retrieve", json={'src': self.src, 'dst': self.dst}) as res:
            if res.status_code == 404:
                res.success()
            if res.js is None:
                pass

class CPSLoad(FastHttpUser):
    wait_time = default_wait_time

    @task
    def publish(self):
        load = random.choice(loads)
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer ' + load['atis']['pub_bearer']}
        data = {'passports': [load['passport']]}
        with self.rest("POST", load['atis']['pub_url'], name=load['atis']['pub_name'], json=data, headers=headers) as res:
            if res.js is None:
                pass
    
    @task
    def retrieve(self):
        load = random.choice(loads)
        get_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer ' + load['atis']['ret_bearer']}
        with self.rest("GET", load['atis']['ret_url'], name=load['atis']['ret_name'], headers=get_headers) as res:
            if res.status_code == 404:
                res.success() # Possibly no data to retrieve
            if res.js is None:
                pass

class CPeXLoad(FastHttpUser):
    wait_time = default_wait_time

    @task(2) # 2 times more likely to generate cid for each call
    def cidgeneration(self):
        load = random.choice(loads)
        tasks = [
            gevent.spawn(self.rest, "POST", f'{ev_url}/evaluate', name=ev_url, json=load['cpex']['oprf']) for ev_url in load['cpex']['evs']
        ]
        gevent.joinall(tasks)
    
    @task
    def publish(self):
        load = random.choice(loads)
        data = {
            'idx': load['cpex']['idx'], 
            'ctx': load['cpex']['ctx'], 
            'sig': load['cpex']['pub_sig']
        }
        tasks = [
            gevent.spawn(self.rest, "POST", f'{ms_url}/publish', name=ms_url, json=data) for ms_url in load['cpex']['mss']
        ]
        gevent.joinall(tasks)
        
    @task
    def retrieve(self):
        load = random.choice(loads)
        data = {
            'idx': load['cpex']['idx'], 
            'sig': load['cpex']['ret_sig']
        }
        tasks = [
            gevent.spawn(self.rest, "POST", f'{ms_url}/retrieve', name=ms_url, json=data) for ms_url in load['cpex']['mss']
        ]
        gevent.joinall(tasks)
