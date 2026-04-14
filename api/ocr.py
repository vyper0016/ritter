from receipt import Receipt
from abc import ABC, abstractmethod
import misc

OCR_PROVIDER = misc.get_config("OCR_PROVIDER", "veryfi")

def get_ocr_provider() -> "OCRProvider":
    match OCR_PROVIDER:
        case "veryfi":
            from veryfi_ocr import VeryfiProvider
            _provider = VeryfiProvider()
        case _:
            raise ValueError(f"Unsupported OCR provider: {OCR_PROVIDER}")
    return _provider
    
class OCRProvider(ABC):
    @abstractmethod
    def process_document(self, file_path: str) -> "Receipt":
        pass
