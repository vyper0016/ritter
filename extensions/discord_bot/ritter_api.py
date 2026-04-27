import os
import requests
from pathlib import Path
from dotenv import load_dotenv
import json
from typing import Any

dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)


API_URL = os.getenv("API_URL", '')
assert API_URL, "API_URL environment variable is not set"

def test_api_health() -> None:
    response = requests.get(API_URL+"/health")
    response.raise_for_status()
    print("ritter API is healthy")
    
def test_api_key(api_key: str) -> dict:
    headers = {"X-API-Key": api_key}
    response = requests.get(API_URL+"/test", headers=headers)
    response.raise_for_status()
    return response.json()

def upload_receipt(
    api_key: str,
    image_path: str,
    payer_id: str,
    uploaded_through: str = "discord bot",
    participant_ids: str = "-1",
) -> dict[str, Any]:
    url = API_URL + "/receipts"
    headers = {
        "X-API-Key": api_key
    }

    image_file = Path(image_path)
    with image_file.open("rb") as file_handle:
        files = {
            "image": (image_file.name, file_handle, "image/jpeg"),
        }
        data = {
            "payer_id": payer_id,
            "participant_ids": participant_ids,
            "uploaded_through": uploaded_through
        }
        response = requests.post(url, headers=headers, files=files, data=data)

    response.raise_for_status()
    return response.json()

def get_users() -> list:
    response = requests.get(API_URL+"/users")
    response.raise_for_status()
    return response.json()    
