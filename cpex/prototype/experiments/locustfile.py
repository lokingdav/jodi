from locust import task, FastHttpUser, between
from pylibcpex import Utils, Oprf
from cpex.crypto import groupsig, libcpex
from cpex.helpers import misc
import random
from cpex.models import cache
from cpex.prototype.simulations import local

size = random.randint(32, 128)
cache.set_client(cache.connect())
local.LocalSimulator.create_cpex_nodes(20, 20)

class EV(FastHttpUser):
    wait_time = between(0.5, 1.5)
    
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
    wait_time = between(0.5, 1.5)
    
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