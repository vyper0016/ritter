from pydantic import BaseModel, Field
from api.vendor import Vendor
from api.line_item import LineItem
from api.payment import Payment
from datetime import datetime, timedelta

class Receipt(BaseModel):
    date: datetime | None = None
    vendor: Vendor | None = None
    line_items: list[LineItem]
    total: float
    payment: Payment | None = None
    ocr_score: float | None = None
    raw_response: dict = Field(default_factory=dict)
    
    
    @staticmethod
    def empty_receipt() -> "Receipt":
        """Returns a new empty receipt with default values."""
        return Receipt(
            date=datetime.now() - timedelta(minutes=1),  # Set to 1 minute in the past to satisfy PastDatetime
            line_items=[],
            total=0
        )
    
    def total_valid(self):
        expected_total = .0
        expected_total = sum(item.total for item in self.line_items)
        return abs(self.total - expected_total) < 0.01
    
if __name__ == "__main__":
    # Example usage
    receipt = Receipt(
        date=datetime.fromisoformat("2024-01-01T12:00:00"),
        line_items=[
            LineItem(description="Widget", quantity=2, price=3.50, total=7.00, order=0),
            LineItem(description="Gadget", quantity=1, price=5.00, total=5.00, order=1)
        ],
        total=2 * 3.50 + 1 * 5.00
    )
    print(Receipt.empty_receipt())