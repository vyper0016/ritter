import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT_DIR / "samples"
sys.path.insert(0, str(ROOT_DIR))

from api.veryfi_ocr import VeryfiProvider, client_from_config

RECEIPTS_DIR = SAMPLES_DIR / "receipts"
RESPONSES_DIR = SAMPLES_DIR / "responses"
OUTPUTS_DIR = SAMPLES_DIR / "outputs"


class CachedClient():
    """Serves saved Veryfi responses; calls the real API only when none is saved."""
    def __init__(self):
        self.client = None

    def process_document(self, file_path, delete_after_processing=True):
        response_path = RESPONSES_DIR / f"{Path(file_path).name}.json"
        if response_path.exists():
            with open(response_path, "r", encoding="utf-8") as f:
                return json.load(f)

        if self.client is None:
            self.client = client_from_config()
        print(f"  fetching {Path(file_path).name} from Veryfi...")
        response = self.client.process_document(file_path, delete_after_processing=delete_after_processing)
        with open(response_path, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        return response


def main():
    RESPONSES_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)

    # Only fetch for receipts without an output; re-parse everything that has a saved response.
    receipts = [
        name for name in sorted(os.listdir(RECEIPTS_DIR))
        if (RESPONSES_DIR / f"{name}.json").exists() or not (OUTPUTS_DIR / f"{name}.json").exists()
    ]
    provider = VeryfiProvider(CachedClient())

    print(f"Processing {len(receipts)} receipts...")
    for i, name in enumerate(receipts):
        print(f"Processing {name} {i + 1}/{len(receipts)}...")
        receipt = provider.process_document(str(RECEIPTS_DIR / name))
        with open(OUTPUTS_DIR / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(receipt.model_dump(mode="json"), f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
