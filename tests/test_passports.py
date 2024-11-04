import unittest
from uuid import uuid4
import time
import jwt

from cpex.stirshaken.passports import (
    certs,
    Passport,
    PassportHeader,
    PassportPayload,
    TNModel
)

orig_tn, dest_tn, alg = "+1234567890", "+1987654321", "RS256"

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


class TestTNModel(unittest.TestCase):
    def test_tn_model_creation(self):
        tn = orig_tn
        model = TNModel(tn=tn)
        self.assertEqual(model.tn, tn)


class TestPassportHeader(unittest.TestCase):
    def test_passport_header_to_dict(self):
        header = PassportHeader(
            x5u="https://example.com/cert.pem",
            alg=alg
        )
        header_dict = header.to_dict()
        expected = {
            "ppt": "shaken",
            "typ": "passport",
            "x5u": "https://example.com/cert.pem",
            "alg": alg
        }
        self.assertEqual(header_dict, expected)

    def test_passport_header_from_dict(self):
        data = {
            "ppt": "shaken",
            "typ": "passport",
            "x5u": "https://example.com/cert.pem",
            "alg": alg
        }
        header = PassportHeader.from_dict(data)
        self.assertEqual(header.ppt, "shaken")
        self.assertEqual(header.typ, "passport")
        self.assertEqual(header.x5u, "https://example.com/cert.pem")
        self.assertEqual(header.alg, alg)


class TestPassportPayload(unittest.TestCase):
    def test_passport_payload_to_dict(self):
        orig = TNModel(tn=orig_tn)
        dest = TNModel(tn=dest_tn)
        payload = PassportPayload(
            attest='A',
            orig=orig,
            dest=dest
        )
        payload_dict = payload.to_dict()
        self.assertEqual(payload_dict['attest'], 'A')
        self.assertEqual(payload_dict['orig']['tn'], orig_tn)
        self.assertEqual(payload_dict['dest']['tn'], dest_tn)
        self.assertIn('iat', payload_dict)
        self.assertIn('origid', payload_dict)

    def test_passport_payload_from_dict(self):
        data = {
            "attest": "B",
            "orig": {"tn": orig_tn},
            "dest": {"tn": dest_tn},
            "iat": int(time.time()),
            "origid": str(uuid4())
        }
        payload = PassportPayload.from_dict(data)
        self.assertEqual(payload.attest, "B")
        self.assertEqual(payload.orig.tn, orig_tn)
        self.assertEqual(payload.dest.tn, dest_tn)
        self.assertEqual(payload.iat, data['iat'])
        self.assertEqual(payload.origid, data['origid'])


class TestPassport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate RSA key pair
        cls.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        cls.public_key = cls.private_key.public_key()

        # Serialize private key to PEM format
        cls.private_key_pem = cls.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Serialize public key to PEM format
        cls.public_key_pem = cls.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        # Define a test certificate URL (can be any string since we're not fetching it)
        cls.test_x5u = "https://example.com/test_cert.pem"

        # Store original certs functions to restore later
        cls.original_get_private_key = certs.get_private_key
        cls.original_get_public_key_from_cert = certs.get_public_key_from_cert

        # Override certs.get_private_key to return the generated private key
        def mock_get_private_key(key_id: str) -> str:
            return cls.private_key_pem

        certs.get_private_key = mock_get_private_key

        # Override certs.get_public_key_from_cert to return the generated public key
        def mock_get_public_key_from_cert(x5u: str) -> str:
            if x5u == cls.test_x5u:
                return cls.public_key_pem
            raise ValueError("Unknown certificate URL")

        certs.get_public_key_from_cert = mock_get_public_key_from_cert

    @classmethod
    def tearDownClass(cls):
        # Restore original certs functions
        certs.get_private_key = cls.original_get_private_key
        certs.get_public_key_from_cert = cls.original_get_public_key_from_cert

    def setUp(self):
        self.header_data = {
            "ppt": "shaken",
            "typ": "passport",
            "x5u": self.__class__.test_x5u,
            "alg": alg
        }
        self.payload_data = {
            "attest": "A",
            "orig": {"tn": orig_tn},
            "dest": {"tn": dest_tn},
            "iat": int(time.time()),
            "origid": str(uuid4())
        }
        self.header = PassportHeader(**self.header_data)
        self.payload = PassportPayload(**self.payload_data)
        self.passport = Passport(header=self.header, payload=self.payload)

    def test_sign_passport(self):
        jwt_token = self.passport.sign("key_identifier")

        # Check that jwt_token is set
        self.assertIsNotNone(jwt_token)

        # Decode the token to verify its content
        decoded = jwt.decode(
            jwt_token,
            self.__class__.public_key_pem,
            algorithms=[self.header.alg]
        )

        # Verify payload
        self.assertEqual(decoded['attest'], self.payload_data['attest'])
        self.assertEqual(decoded['orig']['tn'], self.payload_data['orig']['tn'])
        self.assertEqual(decoded['dest']['tn'], self.payload_data['dest']['tn'])

        # Verify header
        unverified_header = jwt.get_unverified_header(jwt_token)
        self.assertEqual(unverified_header['ppt'], self.header_data['ppt'])
        self.assertEqual(unverified_header['typ'], self.header_data['typ'])
        self.assertEqual(unverified_header['x5u'], self.header_data['x5u'])
        self.assertEqual(unverified_header['alg'], self.header_data['alg'])

        self.assertTrue(jwt_token is not None)

    def test_verify_jwt_token(self):
        # Sign the passport first
        token = self.passport.sign("key_identifier")

        # Now verify the token
        pp = Passport.verify_jwt_token(token, self.__class__.public_key_pem)

        # Check that is_verified is True
        self.assertTrue(pp.is_verified)

        # Check that the payload matches
        self.assertEqual(pp.payload.attest, self.payload_data['attest'])
        self.assertEqual(pp.payload.orig.tn, self.payload_data['orig']['tn'])
        self.assertEqual(pp.payload.dest.tn, self.payload_data['dest']['tn'])

        # Check the header
        self.assertEqual(pp.header.ppt, self.header_data['ppt'])
        self.assertEqual(pp.header.typ, self.header_data['typ'])
        self.assertEqual(pp.header.x5u, self.header_data['x5u'])
        self.assertEqual(pp.header.alg, self.header_data['alg'])

        # Check the token
        self.assertEqual(pp.jwt_token, token)


    def test_get_orig_tn(self):
        self.assertEqual(self.passport.get_orig_tn(), orig_tn)

    def test_get_dest_tn(self):
        self.assertEqual(self.passport.get_dest_tn(), dest_tn)

    def test_passport_creation(self):
        self.assertEqual(self.passport.header.ppt, "shaken")
        self.assertEqual(self.passport.header.typ, "passport")
        self.assertEqual(self.passport.header.x5u, self.__class__.test_x5u)
        self.assertEqual(self.passport.header.alg, alg)
        self.assertEqual(self.passport.payload.attest, "A")
        self.assertEqual(self.passport.payload.orig.tn, orig_tn)
        self.assertEqual(self.passport.payload.dest.tn, dest_tn)
        self.assertFalse(self.passport.is_verified)
        self.assertIsNone(self.passport.jwt_token)


if __name__ == '__main__':
    unittest.main()
