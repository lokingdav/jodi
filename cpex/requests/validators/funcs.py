from cpex.prototype.stirshaken.passports import Passport

def validate_passport(token: str) -> str:
    assert Passport.verify_jwt_token(token=token) is not None, f"'{token}' is invalid"
    return token