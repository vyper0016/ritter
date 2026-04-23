from abc import ABC, abstractmethod
from api.receipt import Receipt
import api.misc as misc

OCR_PROVIDER = misc.get_config("OCR_PROVIDER", "veryfi")


def get_ocr_provider() -> "OCRProvider":
    match OCR_PROVIDER:
        case "veryfi":
            from api.veryfi_ocr import VeryfiProvider
            return VeryfiProvider.from_config()
        case _:
            raise ValueError(f"Unsupported OCR provider: {OCR_PROVIDER}")


class OCRProvider(ABC):
    @abstractmethod
    def process_document(self, file_path: str) -> Receipt:
        pass
