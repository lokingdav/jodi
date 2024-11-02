from pydantic import BaseModel
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field

phone_regex = r"^\+[1-9]\d{1,14}$"

class AtisRetrieve(BaseModel):
    orig: Annotated[
        str, 
        Field(pattern=phone_regex, description="Origin phone number in E.164 format (e.g., +123456789)")
    ]
    dest: Annotated[
        str, 
        Field(pattern=phone_regex, description="Destination phone number in E.164 format (e.g., +123456789)")
    ]
    token: Annotated[
        str, 
        Field(description="JWT for authenticating the retrieve request")
    ]



class AtisPublish(BaseModel):
    orig: str
    dest: str
    passports: List[str]
    
class AtisRepublish(AtisPublish):
    tokens: List[str]
    
class CpexPublish(BaseModel):
    sig: str
    idx: str
    ctx: str
    
class CpexReplicate(BaseModel):
    payload: CpexPublish
    route: str
    sig: str
    
class CpexRetrieve(BaseModel):
    idx: str
    sig: str
    
class PublishFormReq(BaseModel):
    atis: Optional[AtisPublish]
    cpex: Optional[CpexPublish]

class RepublishFormReq(BaseModel):
    atis: Optional[AtisRepublish]
    cpex: Optional[CpexReplicate]
    
class RetrieveFormReq(BaseModel):
    atis: AtisRetrieve
    cpex: CpexRetrieve
