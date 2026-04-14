from veryfi_ocr import VeryfiProvider
from misc import get_config
import os
import json


receipts = os.listdir("samples/receipts")

class DummyClient():
    def process_document(self, file_path, delete_after_processing=True):
        with open(file_path.replace("receipts", "responses")+".json", "r") as f:
            return json.load(f)            

provider = VeryfiProvider(DummyClient())

print(f"Processing {len(receipts)} receipts...")

for i, sample_receipt in enumerate(receipts):
    print(f"Processing {sample_receipt} {i + 1}/{len(receipts)}...")
    receipt = provider.process_document(os.path.join("samples/receipts", sample_receipt))
    print('passed')
    with open(os.path.join("samples/outputs", sample_receipt+".json"), "w", encoding="utf-8") as f:
        json.dump(receipt.model_dump(mode="json"), f, indent=4, ensure_ascii=False)
