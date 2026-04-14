import os

IN_DOCKER = os.path.exists("/.dockerenv")
if not IN_DOCKER:
    import json
    with open("creds.json", "r") as f:
        creds = json.load(f)

def get_config(key: str, default: str = "") -> str:
    if IN_DOCKER:
        return os.getenv(key, default)
    else:
        return creds.get(key, default)
        