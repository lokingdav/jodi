from cpex import config
from typing import List
from cpex.helpers import misc, http
from cpex.prototype.stirshaken.auth_service import AuthService

class OobSSIWF:
    def __init__(self, params: dict):
        self.pid = params['pid']
        self.SPC = f'sp_{self.pid}'
        self.logger = params.get('logger')
        
        self.cps_fqdn = params['cps']['fqdn']
        self.cr_sk = params['cr']['sk']
        self.cr_x5u = params['cr']['x5u']
        
        self.load_auth_service()
        
    def load_auth_service(self):
        self.auth_service = AuthService(
            ownerId=self.pid,
            private_key_pem=self.cr_sk,
            x5u=self.cr_x5u,
        )
        
    def log_msg(self, msg):
        if config.DEBUG and self.logger:
            self.logger.debug(msg)
        
    async def atis_retrieve_token(self, src: str, dst: str) -> str:
        self.log_msg(f'--> Executes ATIS RETRIEVE')
        authorization: str = self.auth_service.authenticate_request(
            action='retrieve',
            orig=src,
            dest=dst,
            passports=[],
            iss=self.pid,
            aud=self.cps_fqdn
        )
        
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        url = f'http://{self.cps_fqdn}/retrieve/{dst}/{src}'
        
        self.log_msg(f'--> RETRIEVE URL: {url}')
        response = await http.get(url=url, params={}, headers=headers)
        self.log_msg(f"ATIS RETRIEVE Response: {response}")
        if type(response) == list and len(response) > 0:
            return response[0]
        return response
    
    async def atis_publish_token(self, src: str, dst: str, identity: str):
        self.log_msg(f'--> Executes ATIS PUBLISH')
        authorization: str = self.auth_service.authenticate_request(
            action='publish',
            orig=src,
            dest=dst,
            passports=[identity],
            iss=self.pid,
            aud=self.cps_fqdn
        )
        # self.log_msg(f'Authorized Request with: Bearer {authorization}')
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        payload: dict = {'passports': [ identity ]}
        url = f'http://{self.cps_fqdn}/publish/{dst}/{src}'
        self.log_msg(f'--> PUBLISH URL: {url}')
        responses = await http.posts(reqs=[{'url': url, 'data': payload, 'headers': headers}])
        self.log_msg(f"ATIS PUBLISH Responses: {responses}")
        return responses