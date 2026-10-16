import re
from veryfi import Client
from api.misc import get_config
from api.receipt import Receipt
from api.vendor import Vendor
from api.line_item import LineItem
from api.payment import Payment
from api.ocr import OCRProvider

# German base price line, e.g. "79,00 € je 1 l." / "0,10 € je 1 St."
BASE_PRICE_LINE = re.compile(r"\d+,\d{2}\s*\S?\s*je\s+1\s+\w+\.?\s*$")

class VeryfiProvider(OCRProvider):
    def __init__(self, client):
        self.client = client
        
    @classmethod
    def from_config(cls):
        client = Client(get_config("VERYFI_CLIENT_ID"), get_config("VERYFI_CLIENT_SECRET"), get_config("VERYFI_USERNAME"), get_config("VERYFI_API_KEY"))
        return cls(client)
    
    def test_connection(self) -> None:
        self.client.get_documents()

    def process_document(self, file_path: str) -> Receipt:
        response = self.client.process_document(file_path, delete_after_processing=True)
        if not response.get("line_items", []):
            return Receipt.empty_receipt()
        
        line_items = self.parse_line_items(response.get("line_items"))
        response.pop("line_items")
     
        vendor = Vendor(
            name=response["vendor"].get("name"),
            address=response["vendor"].get("address"),
            category=response["vendor"].get("category"),
            logo=response["vendor"].get("logo"),
            raw_response=response["vendor"]
        )
        response.pop("vendor")
        
        payment = Payment(
            type=response['payment'].get("payment_type"),
            card_number=response['payment'].get("card_number"),
            display_name=response['payment'].get("display_name"),
            raw_response=response['payment']
        )
        response.pop("payment")
        
        response.pop("ocr_text", None) # Remove ocr_text from raw_response to save space
        return Receipt(
            date=response.get("date"),
            vendor=vendor,
            line_items=line_items,
            total=response.get("total"),
            payment=payment,
            ocr_score=response['meta'].get("ocr_score"),
            raw_response=response
        )

    @staticmethod
    def merge_base_price_lines(line_items_response: list[dict]) -> list[dict]:
        """
        Veryfi splits two-line items (e.g. dm online invoices) into two line items:
            "Rexona                                    3,95 € (1)   1   3,95 €"
            "Antitranspirant Deostick ..., 50 ml       79,00 € je 1 l."
        The second line only holds the product name and the base price (Grundpreis), which
        Veryfi reports as an extra item. Fold its name into the previous item and drop it.
        """
        merged = []
        for item in line_items_response:
            text = item.get("text") or ""
            if merged and BASE_PRICE_LINE.search(text):
                name = (item.get("description") or text).split("\n")[0].split("\t")[0].strip()
                prev = merged[-1]
                prev["description"] = f"{prev.get('description') or ''} {name}".strip()
                continue
            merged.append(dict(item))
        return merged

    @staticmethod
    def parse_line_items(line_items_response: list[dict]):
        line_items = []
        for item in VeryfiProvider.merge_base_price_lines(line_items_response):
            total = item.get("total")
            quantity = item.get("quantity")
            price = item.get("price")
            if price is None:
                assert quantity == 1, "Unexpected API Response: If price is not provided, quantity must be 1"
                price = total
                
            if total and price and total < 0 and price > 0: # Handle negative total with positive price (e.g. discounts)
                price = -price
            
            line_items.append(LineItem(
                description=item.get("description"),
                quantity=quantity,
                price=price,
                total=total,
                order=item.get("order"),
                type=item.get("type"),
                unit_of_measure=item.get("unit_of_measure"),
                raw_response={k: v for k, v in item.items() if v == 0 or v} # strip null values to save space
            ))
        return line_items
        