import json, os
from dotenv import dotenv_values
from typing import List

def is_empty(fileloc: str):
    if not os.path.exists(fileloc):
        return True
    return os.path.isfile(fileloc) and os.path.getsize(fileloc) == 0

def override_json(fileloc: str, data: dict, indent: int = 2):
    with open(fileloc, 'w') as file:
        file.write(json.dumps(data, indent=indent))
    return True

def write_csv(fileloc: str, data: list):
    with open(fileloc, 'w') as file:
        for row in data:
            file.write(", ".join([str(x) for x in row]) + "\n")
    return True

def append_csv(fileloc: str, data: List[List[str]]):
    with open(fileloc, 'a') as file:
        for row in data:
            file.write(", ".join([str(x) for x in row]) + "\n")
    return True

def read_json(fileloc: str, default: dict = None):
    if is_empty(fileloc):
        return False if default is None else default
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
            
def create_dir_if_not_exists(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory '{path}': {e}")

def delete_file(fileloc: str):
    try:
        os.remove(fileloc)
    except Exception as e:
        print(f"Error deleting file '{fileloc}': {e}")