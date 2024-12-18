import json, os

def is_empty(fileloc: str):
    if not os.path.exists(fileloc):
        return True
    return os.path.isfile(fileloc) and os.path.getsize(fileloc) == 0

def override_json(fileloc: str, data: dict, indent: int = 2):
    with open(fileloc, 'w') as file:
        file.write(json.dumps(data, indent=indent))
    return True

def read_json(fileloc: str):
    if is_empty(fileloc):
        return False
    data: dict = {}
    with open(fileloc) as file:
        data = json.loads(file.read())
    return data