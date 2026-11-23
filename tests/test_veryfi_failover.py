from types import SimpleNamespace

import pytest
from veryfi.errors import VeryfiClientError

import api.veryfi_ocr as veryfi_ocr
from api.veryfi_ocr import FailoverClient


def veryfi_error(status: int) -> VeryfiClientError:
    return VeryfiClientError(SimpleNamespace(status_code=status), error=f"error {status}")


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def process_document(self, file_path, delete_after_processing=True):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    def get_documents(self):
        return self.process_document("")


def test_primary_used_when_it_works():
    primary, backup = FakeClient({"id": 1}), FakeClient({"id": 2})
    assert FailoverClient([primary, backup]).process_document("x.pdf") == {"id": 1}
    assert backup.calls == 0


@pytest.mark.parametrize("status", [401, 402, 403, 409, 429])
def test_backup_used_when_primary_key_fails(status):
    primary, backup = FakeClient(error=veryfi_error(status)), FakeClient({"id": 2})
    client = FailoverClient([primary, backup])
    assert client.process_document("x.pdf") == {"id": 2}
    assert client.get_documents() == {"id": 2}


@pytest.mark.parametrize("status", [400, 404, 500])
def test_other_errors_not_retried(status):
    primary, backup = FakeClient(error=veryfi_error(status)), FakeClient({"id": 2})
    with pytest.raises(VeryfiClientError):
        FailoverClient([primary, backup]).process_document("x.pdf")
    assert backup.calls == 0


def test_last_error_raised_when_all_keys_fail():
    error = veryfi_error(409)
    client = FailoverClient([FakeClient(error=veryfi_error(401)), FakeClient(error=error)])
    with pytest.raises(VeryfiClientError) as exc_info:
        client.process_document("x.pdf")
    assert exc_info.value is error


def make_client_from(config: dict, monkeypatch):
    monkeypatch.setattr(veryfi_ocr, "get_config", lambda key, default="": config.get(key, default))
    monkeypatch.setattr(veryfi_ocr, "Client", lambda *args: args)
    return veryfi_ocr.client_from_config().clients


PRIMARY = {"VERYFI_CLIENT_ID": "id", "VERYFI_CLIENT_SECRET": "secret", "VERYFI_USERNAME": "user", "VERYFI_API_KEY": "key"}


def test_no_backup_without_backup_key(monkeypatch):
    assert make_client_from(PRIMARY, monkeypatch) == [("id", "secret", "user", "key")]


def test_backup_reuses_primary_creds(monkeypatch):
    clients = make_client_from({**PRIMARY, "VERYFI_API_KEY_BACKUP": "key2"}, monkeypatch)
    assert clients == [("id", "secret", "user", "key"), ("id", "secret", "user", "key2")]


def test_backup_with_own_account(monkeypatch):
    config = {**PRIMARY, "VERYFI_API_KEY_BACKUP": "key2", "VERYFI_CLIENT_ID_BACKUP": "id2",
              "VERYFI_CLIENT_SECRET_BACKUP": "secret2", "VERYFI_USERNAME_BACKUP": "user2"}
    assert make_client_from(config, monkeypatch)[1] == ("id2", "secret2", "user2", "key2")
