import os
import base64
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID

from cpex.stirshaken.certs import (
    generate_key_pair,
    create_csr,
    sign_csr,
    get_private_key,
)

def create_self_signed_cert(private_key_str: str, subject: x509.Name, days_valid: int = 365) -> str:
    """
    Creates a self-signed certificate using the provided private key and subject.

    Args:
        private_key_str: The PEM-formatted private key as a string.
        subject: An x509.Name object representing the subject's distinguished name.
        days_valid: Number of days the certificate is valid for.

    Returns:
        The self-signed certificate as a PEM-formatted string.
    """
    private_key = get_private_key(private_key_str)
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

def update_env_file(env_vars: dict, env_file_path: str = '.env'):
    """
    Updates the .env file with the provided environment variables.

    Args:
        env_vars: A dictionary of environment variables to update.
        env_file_path: The path to the .env file.
    """
    # Read existing environment variables
    existing_vars = {}
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, val = line.strip().split('=', 1)
                    existing_vars[key] = val

    # Update with new variables
    existing_vars.update(env_vars)

    # Write back to the .env file
    with open(env_file_path, 'w') as f:
        for key, val in existing_vars.items():
            # Base64 encode the values to handle multiline strings
            val_encoded = base64.b64encode(val.encode()).decode()
            f.write(f'{key}={val_encoded}\n')

def main():
    # Generate Root CA key pair and self-signed certificate
    root_private_key_str, root_public_key_str = generate_key_pair()
    root_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"Root CA"),
    ])
    root_cert_str = create_self_signed_cert(root_private_key_str, root_subject)

    # Generate Intermediate CA key pair
    intermediate_private_key_str, intermediate_public_key_str = generate_key_pair()
    intermediate_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"Intermediate CA"),
    ])
    # Create CSR for Intermediate CA
    intermediate_csr_str = create_csr(
        private_key_str=intermediate_private_key_str,
        common_name="Intermediate CA",
        country_name="US",
        state_or_province_name="California",
        locality_name="San Francisco",
        organization_name="My Company"
    )
    # Sign Intermediate CA CSR with Root CA to create Intermediate CA certificate
    intermediate_cert_str = sign_csr(intermediate_csr_str, root_private_key_str, root_cert_str)

    # Update the .env file with the keys and certificates
    env_vars = {
        'ROOT_PRIVATE_KEY': root_private_key_str,
        'ROOT_CERTIFICATE': root_cert_str,
        'INTERMEDIATE_PRIVATE_KEY': intermediate_private_key_str,
        'INTERMEDIATE_CERTIFICATE': intermediate_cert_str,
    }
    update_env_file(env_vars)

    print("Root CA and Intermediate CA keys and certificates have been generated and stored in .env file.")

if __name__ == '__main__':
    main()
