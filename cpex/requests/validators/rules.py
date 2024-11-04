from typing import Annotated
from pydantic import Field
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