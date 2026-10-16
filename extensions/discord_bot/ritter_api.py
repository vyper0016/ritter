import os
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
import json
from typing import Any

dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

logger = logging.getLogger("ritter_api")

API_URL = os.getenv("API_URL", '')
assert API_URL, "API_URL environment variable is not set"

# (connect, read) timeout in seconds - without it a hung request blocks forever
TIMEOUT = (10, 120)


def _raise_for_status(response: requests.Response) -> None:
    """Like response.raise_for_status(), but logs and includes the response body."""
    if response.ok:
        return
    body = response.text[:1000]
    logger.error(
        "%s %s -> HTTP %s: %s",
        response.request.method, response.url, response.status_code, body,
    )
    raise requests.HTTPError(
        f"HTTP {response.status_code} from {response.request.method} {response.url}: {body}",
        response=response,
    )


def test_api_health() -> None:
    response = requests.get(API_URL+"/health", timeout=TIMEOUT)
    _raise_for_status(response)
    logger.info("ritter API is healthy (%s)", API_URL)

def test_api_key(api_key: str) -> dict:
    headers = {"X-API-Key": api_key}
    response = requests.get(API_URL+"/test", headers=headers, timeout=TIMEOUT)
    _raise_for_status(response)
    return response.json()

def upload_receipt(
    api_key: str,
    image_path: str,
    payer_id: str,
    content_type: str = "image/jpeg",
    uploaded_through: str = "discord bot",
    participant_ids: str = "-1",
) -> dict[str, Any]:
    url = API_URL + "/receipts"
    headers = {
        "X-API-Key": api_key
    }

    image_file = Path(image_path)
    logger.info(
        "POST %s file=%s size=%d content_type=%s payer_id=%s",
        url, image_file.name, image_file.stat().st_size, content_type, payer_id,
    )
    with image_file.open("rb") as file_handle:
        files = {
            "image": (image_file.name, file_handle, content_type),
        }
        data = {
            "payer_id": payer_id,
            "participant_ids": participant_ids,
            "uploaded_through": uploaded_through
        }
        response = requests.post(url, headers=headers, files=files, data=data, timeout=TIMEOUT)

    _raise_for_status(response)
    return response.json()

def get_users() -> list:
    response = requests.get(API_URL+"/users", timeout=TIMEOUT)
    _raise_for_status(response)
    return response.json()
