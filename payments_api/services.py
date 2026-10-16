from __future__ import annotations

from typing import Any

from . import repository
from .invoice_pipeline import run_all_phases
from .models import PaymentCreate, PaymentRecord, PaymentUpdate


class NotFoundError(ValueError):
    pass


def _to_record(row: dict[str, Any]) -> PaymentRecord:
    return PaymentRecord(**row)


def list_payments() -> list[PaymentRecord]:
    return [_to_record(row) for row in repository.list_payments()]


def get_payment(payment_id: str) -> PaymentRecord:
    row = repository.get_payment(payment_id)
    if row is None:
        raise NotFoundError(f"Payment '{payment_id}' was not found.")
    return _to_record(row)


def list_payments_by_invoice(invoice_id: str) -> list[PaymentRecord]:
    return [_to_record(row) for row in repository.list_payments_by_invoice(invoice_id)]


def create_payment(payload: PaymentCreate) -> PaymentRecord:
    created = repository.create_payment(invoice_id=payload.invoice_id, paid=int(payload.paid))
    return _to_record(created)


def upsert_payment(payment_id: str, payload: PaymentUpdate) -> tuple[PaymentRecord, bool]:
    record, created = repository.upsert_payment(payment_id=payment_id, invoice_id=payload.invoice_id, paid=int(payload.paid))
    return _to_record(record), created


def delete_payment(payment_id: str) -> None:
    deleted = repository.delete_payment(payment_id)
    if not deleted:
        raise NotFoundError(f"Payment '{payment_id}' was not found.")


def get_reconciliation_report() -> dict[str, Any]:
    api_payments = repository.list_payments()
    pipeline_payments = [{"invoice_id": row["invoice_id"], "paid": row["paid"]} for row in api_payments]
    return run_all_phases(payments=pipeline_payments)

