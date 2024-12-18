import json, os
from dotenv import dotenv_values, set_key

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

def update_env_file(env_file_path: str, updates: dict):
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"The .env file at '{env_file_path}' does not exist.")

    updated_env = {**dotenv_values(env_file_path), **updates}
    
    with open(env_file_path, "w") as env_file:
        for key, value in updated_env.items():
            env_file.write(f"{key}={value}\n")