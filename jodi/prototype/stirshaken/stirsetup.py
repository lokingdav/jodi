import random
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID

from jodi import constants
import jodi.config as config
from jodi.helpers import files
from jodi.models import persistence
from jodi.prototype.stirshaken import certs

certs_file = config.CONF_DIR + '/certs.json'

states = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 
    'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 
    'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 
    'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 
    'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 
    'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 
    'Wisconsin', 'Wyoming'
]

def create_self_signed_cert(private_key_str: str, subject: x509.Name, days_valid: int = 365) -> str:
    private_key = certs.get_private_key(private_key_str)
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(subject)  # Self-signed
    cert_builder = cert_builder.public_key(private_key.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())
    cert_builder = cert_builder.not_valid_before(datetime.now(timezone.utc))
    cert_builder = cert_builder.not_valid_after(datetime.now(timezone.utc) + timedelta(days=days_valid))
    certificate = cert_builder.sign(private_key=private_key, algorithm=hashes.SHA256())
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return cert_pem

def create_root_ca():
    root_private_key_str, root_public_key_str = certs.generate_key_pair()
    root_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"rca"),
    ])
    return {
        'id': constants.ROOT_CA_KEY,
        constants.PRIV_KEY: root_private_key_str,
        constants.CERT_KEY: create_self_signed_cert(root_private_key_str, root_subject)
    } 

def create_credential(name: str, caprivk: str, cacert: str):
    privk, publk = certs.generate_key_pair()
    
    # Create CSR for credential
    csr_str = certs.create_csr(
        private_key_str=privk,
        common_name=name,
        country_name="US",
        state_or_province_name=states[random.randint(0, len(states) - 1)],
        organization_name=f"ORG {name}"
    )
    
    # Sign CSR with Intermediate CA to create credential certificate
    certificate = certs.sign_csr(csr_str, caprivk, cacert)
    
    return { 'id': name, constants.PRIV_KEY: privk, constants.CERT_KEY: certificate }
    
def setup():
    if not files.is_empty(certs_file):
        print("[SKIPPING] Root and intermediate CAs have already been generated.")
        return files.read_json(certs_file)
    
    root_ca = create_root_ca()
    data = {constants.ROOT_CA_KEY: root_ca}
    for ica in range(int(config.NO_OF_INTERMEDIATE_CAS)):
        ica_name = f"{constants.INTERMEDIATE_CA_KEY}-{ica}"
        data[ica_name] = create_credential(ica_name, root_ca[constants.PRIV_KEY], root_ca[constants.CERT_KEY])
        for i in range(config.NUM_CREDS_PER_ICA):
            idx = ica * config.NUM_CREDS_PER_ICA + i
            ocrt_name = f"{constants.OTHER_CREDS_KEY}-{idx}"
            data[ocrt_name] = create_credential(ocrt_name,  data[ica_name][constants.PRIV_KEY],  data[ica_name][constants.CERT_KEY])
    
    files.override_json(certs_file, data)

    print(f"Certificates have been generated and stored in {certs_file}")

    return data

def load_certs():
    if files.is_empty(certs_file):
        raise Exception(f"Certificates have not been generated")
    creds = files.read_json(certs_file)
    i = random.randint(0, int(config.NO_OF_INTERMEDIATE_CAS) * 10 - 1)
    return creds[f"{constants.OTHER_CREDS_KEY}-{i}"], creds