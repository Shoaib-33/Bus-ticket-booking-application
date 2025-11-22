from pydantic import BaseModel
from typing import List

class Booking(BaseModel):
    name: str
    phone: str
    source: str
    destination: str
    provider: str
    date: str

class SearchQuery(BaseModel):
    source: str
    destination: str
    max_price: int = None
