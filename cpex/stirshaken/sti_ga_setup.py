from collections import defaultdict
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID

from cpex import constants
from cpex.helpers import files
from cpex.stirshaken import certs
import cpex.config as config

ca_certs_file = config.CONF_DIR + '/cas.certs.json'

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
        x509.NameAttribute(NameOID.COMMON_NAME, u"Root CA"),
    ])
    return {
        constants.PRIV_KEY: root_private_key_str,
        constants.CERT_KEY: create_self_signed_cert(root_private_key_str, root_subject)
    } 

def create_intermediate_ca(caconfig: dict):
    # Generate Intermediate CA key pair
    intermediate_private_key_str, intermediate_public_key_str = certs.generate_key_pair()
    
    # Create CSR for Intermediate CA
    intermediate_csr_str = certs.create_csr(
        private_key_str=intermediate_private_key_str,
        common_name="Intermediate CA",
        country_name="US",
        state_or_province_name="California",
        locality_name="San Francisco",
        organization_name="My Company"
    )
    
    # Sign Intermediate CA CSR with Root CA to create Intermediate CA certificate
    intermediate_cert_str = certs.sign_csr(
        intermediate_csr_str, 
        caconfig[constants.ROOT_CA_KEY][constants.PRIV_KEY], 
        caconfig[constants.ROOT_CA_KEY][constants.CERT_KEY]
    )
    
    return {
        constants.PRIV_KEY: intermediate_private_key_str,
        constants.CERT_KEY: intermediate_cert_str
    }
    
def main():
    if not files.is_empty(ca_certs_file):
        print("Root and intermediate CAs have already been generated. Delete certs.json file and rerun to regenerate")
        return True
    
    pki = defaultdict(dict)
    pki[constants.ROOT_CA_KEY] = create_root_ca()
    
    pki[constants.INTERMEDIATE_CA_KEY] = []
    for ica in range(int(config.NO_OF_INTERMEDIATE_CAS)):
        pki[constants.INTERMEDIATE_CA_KEY].append(create_intermediate_ca(pki))
    
    files.override_json(ca_certs_file, pki)

    print(f"Root CA and Intermediate CA keys and certificates have been generated and stored in {ca_certs_file}")

if __name__ == '__main__':
    main()
