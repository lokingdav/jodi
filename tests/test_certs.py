import unittest
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ec

from jodi.prototype.stirshaken.certs import (
    generate_key_pair,
    create_csr,
    sign_csr,
    get_private_key
)

class TestJodiStirShakenCerts(unittest.TestCase):
    def test_generate_key_pair(self):
        """Test generating an elliptic curve key pair."""
        private_key_str, public_key_str = generate_key_pair()
        self.assertIsInstance(private_key_str, str)
        self.assertIsInstance(public_key_str, str)
        # Load the keys to ensure they are valid
        private_key = serialization.load_pem_private_key(private_key_str.encode(), password=None)
        public_key = serialization.load_pem_public_key(public_key_str.encode())
        self.assertIsInstance(private_key, ec.EllipticCurvePrivateKey)
        self.assertIsInstance(public_key, ec.EllipticCurvePublicKey)

    def test_create_csr(self):
        """Test creating a CSR with the provided private key and subject details."""
        private_key_str, _ = generate_key_pair()
        csr_str = create_csr(
            private_key_str=private_key_str,
            common_name='example.com',
            country_name='US',
            state_or_province_name='California',
            locality_name='San Francisco',
            organization_name='Example Inc.'
        )
        self.assertIsInstance(csr_str, str)
        csr = x509.load_pem_x509_csr(csr_str.encode())
        self.assertIsNotNone(csr)
        # Check CSR subject
        subject = csr.subject
        self.assertEqual(subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value, 'example.com')
        self.assertEqual(subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value, 'US')
        self.assertEqual(subject.get_attributes_for_oid(NameOID.STATE_OR_PROVINCE_NAME)[0].value, 'California')
        self.assertEqual(subject.get_attributes_for_oid(NameOID.LOCALITY_NAME)[0].value, 'San Francisco')
        self.assertEqual(subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value, 'Example Inc.')

    def test_sign_csr(self):
        """Test signing a CSR to create a certificate."""
        # Generate CA key pair and self-signed certificate
        ca_private_key_str, ca_public_key_str = generate_key_pair()
        ca_private_key = serialization.load_pem_private_key(ca_private_key_str.encode(), password=None)
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

        # Generate user key pair and CSR
        user_private_key_str, _ = generate_key_pair()
        csr_str = create_csr(
            private_key_str=user_private_key_str,
            common_name='user.example.com',
            country_name='US',
            state_or_province_name='New York',
            locality_name='New York City',
            organization_name='User Inc.'
        )
        # Sign the CSR
        user_cert_str = sign_csr(
            csr_str=csr_str,
            ca_private_key_str=ca_private_key_str,
            ca_cert_str=ca_cert_str,
            days_valid=365
        )
        self.assertIsInstance(user_cert_str, str)
        # Load and verify the certificate
        user_cert = x509.load_pem_x509_certificate(user_cert_str.encode())
        self.assertIsNotNone(user_cert)
        # Verify the certificate's issuer matches the CA
        self.assertEqual(user_cert.issuer, ca_certificate.subject)
        # Verify the certificate's subject matches the CSR's subject
        csr = x509.load_pem_x509_csr(csr_str.encode())
        self.assertEqual(user_cert.subject, csr.subject)
        # Verify the certificate's validity period
        now = datetime.now(timezone.utc)
        self.assertLessEqual(user_cert.not_valid_before_utc, now)
        self.assertGreaterEqual(user_cert.not_valid_after_utc, now)
        # Verify the certificate's public key matches the CSR's public key
        self.assertEqual(
            user_cert.public_key().public_numbers(),
            csr.public_key().public_numbers()
        )

    def test_get_private_key(self):
        """Test loading a private key from a PEM-formatted string."""
        private_key_str, _ = generate_key_pair()
        private_key = get_private_key(private_key_str)
        self.assertIsInstance(private_key, ec.EllipticCurvePrivateKey)
        # Check that the key can sign data
        data = b"test data"
        signature = private_key.sign(
            data,
            ec.ECDSA(ec.ECDSA())
        )
        self.assertIsNotNone(signature)
        # Verify the signature
        public_key = private_key.public_key()
        try:
            public_key.verify(signature, data, ec.ECDSA(ec.ECDSA()))
        except Exception as e:
            self.fail(f"Signature verification failed: {e}")

# Run the tests
if __name__ == '__main__':
    unittest.main()
