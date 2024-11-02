from pydantic import BaseModel

class CSRRequest(BaseModel):
    csr: str