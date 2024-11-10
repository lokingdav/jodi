import json, requests
import cpex.config as config

def post(url: str, data: dict):
    """Post data to a given URL"""
    data = json.dumps(data)
    res = requests.post(url, data)
    res.raise_for_status()
    return res.json()

def multipost(reqs: list):
    pass
    