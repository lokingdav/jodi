import asyncio, argparse, json
from cpex.prototype.provider import Provider
from cpex.helpers import dht
from cpex.models import cache
from cpex.crypto import groupsig

def main():
    payload = {
        'idx': 'dbzv7wD3D0lTtM1l/RfRTWKTnDMXqgRk3Epwp2Mh+qk=', 
        'ctx': 'Hlnv8bLedWZKWaNGSE74HXfKMV4kybw1WtM4jwhlAjU=:OLFjsWrGV/vbuF2T8tzzKQ4Ha1NXa3DcEa4o3+OKovf2kLdEvMJ/cY/IoVOZsbICPwwCSGEcMe6uUCclg+oaMYFDZISdOp0Xski5cyD7W5NKcuIkJANUJu0FXcRGOfACTQTs9jhgOHmWGuQmyvfvcG2tMJFGupYlaXezC9P3avN7cDK+w+6gHgYXOd5yWdBg/MxtZ8oK9XR6pAWbXgWKyKA2UzqYQj9yKYhebBJfAg3O4nojlYsAWGhHnunAMGI32HjIesGRnXthxDV+TjT/9D96FVy+7V9K38Ri7T1tFG1j27ySiUAuVdWjOW5UjS83OQNigkwiiQYkvyvo/NMSqWjB03n5ja82CqWt1nI6yLvIRuSGJU2X+a665JGWEHndRa5UsYTUPu+fpc6tuBC1Mwl9HE73cNKtCYa4ewR5MVnrXFhNX96aKJMvAJU6QUR7GShZnoI1Rvobu9nil7gn2ulki/w=', 
        'sig': 'ATAAAAAh2WRbHPXWLJLt00kSTAjgjqm7N+3yaz0VpJ64tGhuOFtaKFu0T5pzEG8GXVv+9oMwAAAAuad5cXhfksh5OkIW6o0CXjnDtPk3enuy48KhcoYsy3z4tSFs7feyU6xQ5RaWhaSKMAAAAK7dD3uyb0jD4N7E0HHrug4Zfu/2iUysyNCu3f8NUbSJKnR4zPZ839iZEPsP0+WMiiAAAAAI+vgnAxgf8URFEmKb//m9gJB+lRuJscoqSPHyrY5mIiAAAAD59QI/ImkNFB5jlAyz83mlWJ3ufykC02OLq7AgjaATDyAAAABVn1qiqknCxJerwNA9tbIvqcNgIGEX3AMJTDtzBS4lSyAAAABS5i5yic69ZxXu9WYnyw9fTzjMxE4Zz666sD4znS/oVSAAAACPS68QLVG00j/L8x5DI30M48PDK4XXYF1dXspMdGapPCAAAACHxFj3DH0pHg58QNrQfurI2xrrdi2zMSXQQTKqxUchSQ=='
    }
    payload = json.dumps(payload)
    print(len(payload))
    print(len(payload.encode('utf-8')))

if __name__ == '__main__':
    main()