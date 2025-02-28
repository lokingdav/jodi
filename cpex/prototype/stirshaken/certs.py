from cryptography import x509
import validators, requests, traceback
from cryptography.hazmat.primitives import serialization, hashes
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ec

from cpex.helpers import http, mylogging
import cpex.config as config
import cpex.constants as constants

from typing import Tuple

credentials = None

def set_certificate_repository(creds):
    global credentials
    credentials = creds

def generate_key_pair() -> Tuple[str, str]:
    private_key = ec.generate_private_key(
        ec.SECP256R1()  # or SECP384R1, SECP521R1, etc.
    )
    private_key_str = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_key = private_key.public_key()
    public_key_str = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return private_key_str, public_key_str


def create_csr(private_key_str: str, common_name: str, country_name: str = None,
               state_or_province_name: str = None, locality_name: str = None,
               organization_name: str = None) -> str:
    private_key = serialization.load_pem_private_key(
        private_key_str.encode(),
        password=None,
    )
    name_attributes = []

    if country_name:
        name_attributes.append(x509.NameAttribute(x509.NameOID.COUNTRY_NAME, country_name))
    if state_or_province_name:
        name_attributes.append(x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, state_or_province_name))
    if locality_name:
        name_attributes.append(x509.NameAttribute(x509.NameOID.LOCALITY_NAME, locality_name))
    if organization_name:
        name_attributes.append(x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, organization_name))
        
    name_attributes.append(x509.NameAttribute(x509.NameOID.COMMON_NAME, common_name))

    csr_builder = x509.CertificateSigningRequestBuilder()
    csr_builder = csr_builder.subject_name(x509.Name(name_attributes))

    csr = csr_builder.sign(private_key, hashes.SHA256())
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
    return csr_pem


def sign_csr(csr_str: str, ca_private_key_str: str, ca_cert_str: str, days_valid: int = 365) -> str:
    csr = x509.load_pem_x509_csr(csr_str.encode())
    ca_private_key = serialization.load_pem_private_key(
        ca_private_key_str.encode(),
        password=None,
    )
    ca_cert = x509.load_pem_x509_certificate(ca_cert_str.encode())

    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(csr.subject)
    cert_builder = cert_builder.issuer_name(ca_cert.subject)
    cert_builder = cert_builder.public_key(csr.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())
    cert_builder = cert_builder.not_valid_before(datetime.now(timezone.utc))
    cert_builder = cert_builder.not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=days_valid)
    )
    certificate = cert_builder.sign(
        private_key=ca_private_key,
        algorithm=hashes.SHA256()
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return cert_pem


def download(url: str) -> str:
    if config.NODE_FQDN in url:
        key = url.split('/')[-1]
        return credentials[key]['cert']
    
    if not validators.url(url) and not url.startswith('http'):
        raise ValueError(f'Cert url must be a valid URL: {url}')
    try:
        res = requests.get(url=url)
        res.raise_for_status()
        return res.text
    except Exception as e:
        return None


def get_public_key_from_cert(cert: str) -> str:
    try:
        cert: x509.Certificate = x509.load_pem_x509_certificate(cert.encode('utf-8'))
        public_key = cert.public_key()
        pem_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_public_key.decode()
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f'Error getting certificate: {e}')


def get_private_key(key_str: str):
    if not key_str:
        raise ValueError('Must provide a key')
    private_key = serialization.load_pem_private_key(
        key_str.encode(),
        password=None,
    )
    return private_key


def verify_chain_of_trust(certificate_pem: str) -> bool:
    try:
        leaf_cert = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
        cert_chain = [leaf_cert]

        while True:
            current_cert = cert_chain[-1]

            # 1) Detect root by subject == issuer (self-signed).
            if current_cert.issuer == current_cert.subject:
                # Check if that root is in credentials
                # (and optionally verify it's truly self-signed).
                for key, cred_obj in credentials.items():
                    candidate_root = x509.load_pem_x509_certificate(cred_obj["cert"].encode("utf-8"))
                    if (candidate_root.subject == current_cert.subject and 
                        candidate_root.issuer == current_cert.issuer):
                        candidate_root.public_key().verify(
                            candidate_root.signature,
                            candidate_root.tbs_certificate_bytes,
                            ec.ECDSA(candidate_root.signature_hash_algorithm),
                        )
                        _check_certificate_time(candidate_root)
                        return True  # Chain is fully trusted
                raise ValueError("Reached a self-signed cert not in credentials. Chain not trusted.")

            # 2) Otherwise, find issuer in credentials
            issuer_cert = _find_issuer_in_credentials(current_cert.issuer)
            if issuer_cert is None:
                raise ValueError(f"Issuer {current_cert.issuer} not found in credentials. Chain incomplete.")

            issuer_cert.public_key().verify(
                current_cert.signature,
                current_cert.tbs_certificate_bytes,
                ec.ECDSA(current_cert.signature_hash_algorithm)
            )
            _check_certificate_time(current_cert)
            cert_chain.append(issuer_cert)

    except Exception as e:
        traceback.print_exc()
        raise



def _find_issuer_in_credentials(issuer_name: x509.Name):
    cn = issuer_name.rfc4514_string().split(',')[0].split('=')[1]
    cred = credentials.get(cn)
    if not cred:
        return None
    cert_pem = x509.load_pem_x509_certificate(cred["cert"].encode("utf-8"))
    return cert_pem


def _check_certificate_time(cert: x509.Certificate) -> None:
    now = datetime.now(timezone.utc)
    if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
        raise ValueError(f"Certificate {cert.subject} has expired or is not yet valid.")

