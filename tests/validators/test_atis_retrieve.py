import unittest
from pydantic import ValidationError
from cpex.requests.validators.cps_reqs import AtisRetrieve
import jwt
from datetime import datetime, timedelta

class TestAtisRetrieve(unittest.TestCase):
    """Unit tests for the AtisRetrieve Pydantic model."""

    def test_valid_input(self):
        """Test that valid input data with a valid JWT token is accepted."""
        token = 'token'
        data = {
            "orig": "+1234567890",
            "dest": "+19876543210",
            "token": token
        }
        try:
            instance = AtisRetrieve(**data)
        except ValidationError:
            self.fail("AtisRetrieve raised ValidationError unexpectedly with valid input!")
        self.assertEqual(instance.orig, data["orig"])
        self.assertEqual(instance.dest, data["dest"])
        self.assertEqual(instance.token, data["token"])

    def test_invalid_orig_phone(self):
        """Test that an invalid origin phone number raises a ValidationError."""
        token = 'token'
        data = {
            "orig": "1234567890",  # Missing '+' sign
            "dest": "+19876543210",
            "token": token
        }
        with self.assertRaises(ValidationError) as context:
            AtisRetrieve(**data)
        self.assertIn('orig', str(context.exception))

    def test_invalid_dest_phone(self):
        """Test that an invalid destination phone number raises a ValidationError."""
        token = 'token'
        data = {
            "orig": "+1234567890",
            "dest": "19876543210",  # Missing '+' sign
            "token": token
        }
        with self.assertRaises(ValidationError) as context:
            AtisRetrieve(**data)
        self.assertIn('dest', str(context.exception))

    def test_multiple_invalid_fields(self):
        """Test that multiple invalid fields (orig, dest, token) raise a ValidationError with all errors."""
        # Invalid orig and dest, and an invalid token
        data = {
            "orig": "invalid_orig",      # Invalid phone format
            "dest": "invalid_dest",      # Invalid phone format
            "token": "invalid.token"     # Invalid JWT token
        }
        with self.assertRaises(ValidationError) as context:
            AtisRetrieve(**data)
        
        error_message = str(context.exception)
        self.assertIn('orig', error_message)
        self.assertIn('dest', error_message)
        self.assertIn('token', error_message)

    def test_missing_fields(self):
        """Test that missing required fields raise a ValidationError."""
        # Missing 'dest' and 'token'
        data = {
            "orig": "+1234567890",
            # "dest" is missing
            # "token" is missing
        }
        with self.assertRaises(ValidationError) as context:
            AtisRetrieve(**data)
        error_message = str(context.exception)
        self.assertIn('dest', error_message)
        self.assertIn('token', error_message)

   
if __name__ == '__main__':
    unittest.main()
