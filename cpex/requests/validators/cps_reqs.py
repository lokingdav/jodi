from pydantic import BaseModel
from typing import List, Optional, Annotated

import cpex.config as config 
from cpex.requests.validators.rules import PhoneNumberValidator, PassportTokenValidator

class HasPhoneTraits(BaseModel):
    orig: PhoneNumberValidator
    dest: PhoneNumberValidator

class AtisRetrieve(HasPhoneTraits):
    token: PassportTokenValidator

class AtisPublish(HasPhoneTraits):
    passports: List[PassportTokenValidator]
    
class AtisRepublish(HasPhoneTraits):
    tokens: List[PassportTokenValidator]
    
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

#############################################################
# Define Dynamic classes to be used
#############################################################
Publish, Republish, Retrieve = CpexPublish, CpexReplicate, CpexRetrieve

if config.IS_ATIS_MODE:
    Publish, Republish, Retrieve = AtisPublish, AtisRepublish, AtisRetrieve

class PublishRequest(Publish):
    pass

class RepublishRequest(Republish):
    pass

class RetrieveRequest(Retrieve):
    pass