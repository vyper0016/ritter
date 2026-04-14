from pydantic import BaseModel, Field, field_validator

class Payment(BaseModel):
    type: str
    card_number: str | None = None
    display_name: str | None = None
    raw_response: dict = Field(default_factory=dict)
    
    @field_validator('type', 'card_number', 'display_name', mode='before')
    @classmethod
    def none_to_empty_string(cls, v):
        if v is None:
            return ""
        return v