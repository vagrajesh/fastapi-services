from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt


class PaymentCreate(BaseModel):
    invoice_id: str = Field(min_length=1)
    paid: PositiveInt


class PaymentUpdate(BaseModel):
    invoice_id: str = Field(min_length=1)
    paid: PositiveInt


class PaymentRecord(BaseModel):
    payment_id: str = Field(min_length=1)
    invoice_id: str = Field(min_length=1)
    paid: PositiveInt

    class Config:
        extra = "forbid"


class ErrorResponse(BaseModel):
    detail: str
