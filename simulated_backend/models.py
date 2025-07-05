from sqlmodel import SQLModel, Field
from typing import Optional

class Gift(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(index=True,unique=True)
    name: str
    quantity: int

class PurchaseRequest(SQLModel):
    sku: str
    quantity: int

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str
    stars: int
