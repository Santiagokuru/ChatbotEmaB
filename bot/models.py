from pydantic import BaseModel, Field


class ClientInfo(BaseModel):
    name: str
    contact: str = ""


class Item(BaseModel):
    name: str
    quantity: float
    unit_price: float

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)


class ItemList(BaseModel):
    items: list[Item] = Field(default_factory=list)


class QuoteData(BaseModel):
    client: ClientInfo | None = None
    items: list[Item] = Field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)
