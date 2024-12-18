from cryptography import x509
import validators, requests, traceback
from cryptography.hazmat.primitives import serialization, hashes
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ec

from cpex.helpers import http
import cpex.config as config
import cpex.constants as constants

from typing import Tuple

def generate_key_pair() -> Tuple[str, str]:
    """
    Generates an EC private and public key pair.

    Returns:
        A tuple containing the private key and public key as PEM-formatted strings.
    """
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
    """
    Creates a Certificate Signing Request (CSR) using the provided private key and subject details.

    Args:
        private_key_str: The PEM-formatted private key as a string.
        common_name: The Common Name (CN) for the CSR.
        country_name: Country Name (C).
        state_or_province_name: State or Province Name (ST).
        locality_name: Locality Name (L).
        organization_name: Organization Name (O).

    Returns:
        The CSR as a PEM-formatted string.
    """
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
    """
    Signs a CSR using the CA's private key and certificate to create a new certificate.

    Args:
        csr_str: The CSR as a PEM-formatted string.
        ca_private_key_str: The CA's private key as a PEM-formatted string.
        ca_cert_str: The CA's certificate as a PEM-formatted string.
        days_valid: Number of days the certificate is valid for.

    Returns:
        The signed certificate as a PEM-formatted string.
    """
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
    # Add extensions if needed, e.g., KeyUsage, ExtendedKeyUsage, SubjectAlternativeName, etc.

    certificate = cert_builder.sign(
        private_key=ca_private_key,
        algorithm=hashes.SHA256()
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return cert_pem


def download(url: str) -> str:
    if not validators.url(url) and not url.startswith('http'):
        raise ValueError(f'Cert url must be a valid URL: {url}')
    
    try:
        return requests.get(url=url).text
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f'Error getting certificate: {e}')


def get_public_key_from_cert(cert: str) -> str:
    try:
        cert: x509.Certificate = x509.load_pem_x509_certificate(cert.encode())
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

def client_keygen(name: str, country: str = 'US'):
    sk, pk = generate_key_pair()
    csr: str = create_csr(
        private_key_str=sk,
        common_name=name,
        country_name=country
    )
    return sk, csr

def request_cert(csr: str):
    response = http.post(
        url=config.CERT_REPO_BASE_URL + '/sign_csr',
        data={'csr': csr}
    )
    return response.get(constants.CERT_KEY)