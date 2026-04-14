from pydantic import BaseModel, Field, field_validator

class LineItem(BaseModel):
    description: str
    quantity: float
    price: float
    total: float
    order: int # the position of the line item in the receipt, starting from 0
    type: str | None = None
    unit_of_measure: str = ""
    raw_response: dict = Field(default_factory=dict)

    @field_validator('description', 'type', 'unit_of_measure', mode='before')
    @classmethod
    def none_to_empty_string(cls, v):
        if v is None:
            return ""
        return v
    
    @field_validator('quantity', 'price', 'total', mode='before')
    @classmethod
    def none_to_zero(cls, v):
        if v is None:
            return 0.
        return v
    
    @field_validator('total', mode='after')
    @classmethod
    def validate_total(cls, v, info):
        quantity = info.data.get('quantity')
        price = info.data.get('price')
        expected_total = quantity * price
        if abs(v - expected_total) > 0.01:
            raise ValueError(f'total must equal quantity * price ({expected_total})')
        return v
    
if __name__ == "__main__":
    # Example usage
    item = LineItem(description="Widget", order=1, quantity=2, price=3.5, total=7)
    print(item)