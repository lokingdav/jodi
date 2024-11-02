from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from datetime import datetime, timedelta, timezone
from cryptography.x509.oid import NameOID

from cpex.stirshaken.certs import (
    generate_key_pair,
    create_csr,
    sign_csr,
    get_private_key,
)

app = FastAPI()

# In-memory stores for certificates and keys
cert_store: Dict[str, str] = {}
key_store: Dict[str, str] = {}

ca_private_key_str, ca_public_key_str = generate_key_pair()
ca_private_key = get_private_key(ca_private_key_str)
ca_public_key = ca_private_key.public_key()

ca_subject = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, 'My EC CA'),
])

ca_cert_builder = x509.CertificateBuilder()
ca_cert_builder = ca_cert_builder.subject_name(ca_subject)
ca_cert_builder = ca_cert_builder.issuer_name(ca_subject)
ca_cert_builder = ca_cert_builder.public_key(ca_public_key)
ca_cert_builder = ca_cert_builder.serial_number(x509.random_serial_number())
ca_cert_builder = ca_cert_builder.not_valid_before(datetime.now(timezone.utc))
ca_cert_builder = ca_cert_builder.not_valid_after(
    datetime.now(timezone.utc) + timedelta(days=365)
)
ca_certificate = ca_cert_builder.sign(
    private_key=ca_private_key,
    algorithm=hashes.SHA256()
)
ca_cert_str = ca_certificate.public_bytes(serialization.Encoding.PEM).decode()

class CSRRequest(BaseModel):
    csr: str  # The CSR as a PEM-formatted string

@app.get("/certs/{spc}")
async def get_certificate(spc: str):
    """
    Fetches a certificate from the in-memory certificate store based on the SPC (Service Provider Code).
    """
    cert = cert_store.get(spc)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return {"certificate": cert}

@app.post("/sign_csr")
async def sign_csr_endpoint(csr_request: CSRRequest):
    """
    Signs a CSR and issues a certificate using the CA's private key and certificate.
    """
    csr_str = csr_request.csr
    try:
        # Load the CSR to extract the common name (SPC)
        csr = x509.load_pem_x509_csr(csr_str.encode())
        common_name_attributes = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not common_name_attributes:
            raise ValueError("CSR does not contain a Common Name (CN)")

        spc = common_name_attributes[0].value

        # Sign the CSR with the CA's private key
        signed_cert_str = sign_csr(
            csr_str=csr_str,
            ca_private_key_str=ca_private_key_str,
            ca_cert_str=ca_cert_str,
            days_valid=365
        )

        # Store the signed certificate in the cert_store
        cert_store[spc] = signed_cert_str

        return {"certificate": signed_cert_str}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def check_health():
    """
    Health check endpoint to verify that the service is running.
    """
    return {"message": "OK", "status": 200}
