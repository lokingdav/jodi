from typing import Annotated, Literal
from pydantic import Field, HttpUrl
from pydantic.functional_validators import AfterValidator

PhoneNumberValidator = Annotated[str, Field(
    pattern=r"^\+[1-9]\d{1,14}$", 
    min_length=10, 
    max_length=15, 
    description="The Phone number in E.164 format (e.g., +123456789)"
)]

PassportTokenValidator = Annotated[str, Field(
    pattern=r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    description="JWT passport"
)]

AttestationValidator = Literal['A', 'B', 'C']

AlgValidator = Literal['RS256', 'ES256']

x5uValidator = Annotated[str, HttpUrl]