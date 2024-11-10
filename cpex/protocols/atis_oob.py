def get_publish_requests(url: str, token: str, authorization: str) -> tuple[str, dict, dict]:
    headers = {'Authorization': 'Bearer ' + authorization}
    payload = { 'passports': [token] }
    return [(url, headers, payload)]