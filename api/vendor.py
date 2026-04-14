from pydantic import BaseModel, Field, HttpUrl

class Vendor(BaseModel):
    name: str | None = None
    address: str | None = None
    category: str | None = None
    logo: HttpUrl | None = None
    raw_response: dict = Field(default_factory=dict)