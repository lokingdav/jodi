from fastapi import FastAPI, HTTPException
import random
from cryptography import x509
from cryptography.x509.oid import NameOID

import cpex.prototype.stirshaken.certs as sti_certs
import cpex.config as config
from cpex.helpers import errors
from cpex import constants
from cpex.models import persistence, sti_pki
import cpex.prototype.stirshaken.sti_ga_setup as ga_setup
import cpex.helpers.files as files

import traceback

pki = None
ca_certs_file = config.CONF_DIR + '/cas.certs.json'

def init_server():
    global pki
    pki = files.read_json(ca_certs_file)
    if not pki:
        pki = ga_setup.main()
    if not pki:
        raise Exception(errors.ERROR_SETTING_UP_STI_PKI)
    
    return FastAPI()

app = init_server()

@app.get("/certs/{key}")
async def get_certificate(key: str):
    cert = persistence.get_cert(key=key)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return {constants.CERT_KEY: cert}

@app.post("/sign_csr")
async def sign_csr_endpoint(csr_request: sti_pki.CSRRequest):
    """
    Signs a CSR and issues a certificate using a random intermediate CA's private key and certificate.
    """
    csr_str = csr_request.csr
    
    try:
        # Load the CSR to extract the common name
        csr = x509.load_pem_x509_csr(csr_str.encode())
        common_name_attributes = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        
        if not common_name_attributes:
            raise ValueError("CSR does not contain a Common Name (CN)")

        spc = common_name_attributes[0].value
        
        ca = pki[constants.INTERMEDIATE_CA_KEY][random.randint(0, len(pki[constants.INTERMEDIATE_CA_KEY]) - 1)]

        # Sign the CSR with the CA's private key
        signed_cert_str = sti_certs.sign_csr(
            csr_str=csr_str,
            ca_private_key_str=ca[constants.PRIV_KEY],
            ca_cert_str=ca[constants.CERT_KEY],
            days_valid=90
        )

        persistence.store_cert(key=spc, cert=signed_cert_str)

        return {constants.CERT_KEY: signed_cert_str}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def check_health():
    """
    Health check endpoint to verify that the service is running.
    """
    return {"message": "OK", "status": 200}
