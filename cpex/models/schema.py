from pydantic import BaseModel
from typing import List, Dict

class Publish(BaseModel):
    passports: List[str]
    
class Health(BaseModel):
    pass

class Republish(Publish):
    token: str
    
class Retrieve(BaseModel):
    token: str
    passports: List[str]