from pydantic import BaseModel
from typing import List

class PublishFormReq(BaseModel):
    passports: List[str]

class RepublishFormReq(BaseModel):
    token: str
    
class RetrieveFormReq(BaseModel):
    token: str
    passports: List[str]
