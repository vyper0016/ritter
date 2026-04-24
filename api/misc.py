import os
from pathlib import Path

IN_DOCKER = os.path.exists("/.dockerenv")
if not IN_DOCKER:
    import json
    _creds_path = Path(__file__).parent.parent / "creds.json"
    with open(_creds_path, "r") as f:
        creds = json.load(f)

def get_config(key: str, default: str = "") -> str:
    if IN_DOCKER:
        return os.getenv(key, default)
    else:
        return creds.get(key, default)
        