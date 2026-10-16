from __future__ import annotations

from postgres_demo.db_connection import get_connection
import threading
from pathlib import Path
from typing import Any

from .invoice_pipeline import RAW_PAYMENTS



class StorageError(RuntimeError):
    pass


def _seed_payments() -> list[dict[str, Any]]:
    seeded: list[dict[str, Any]] = []
    for idx, row in enumerate(RAW_PAYMENTS, start=1):
        seeded.append(
            {
                "payment_id": f"PAY-{idx:04d}",
                "invoice_id": str(row["invoice_id"]),
                "paid": int(row["paid"]),
            }
        )
    return seeded


def _ensure_store_exists() -> None:
    if PAYMENTS_FILE.exists():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _save_rows(_seed_payments())


def _load_rows() -> list[dict[str, Any]]:
    try:
        _ensure_store_exists()
        with PAYMENTS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageError(f"Failed to read payments store: {exc}") from exc
    if not isinstance(data, list):
        raise StorageError("Payments store is malformed: expected a list.")
    return data


def _save_rows(rows: list[dict[str, Any]]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = PAYMENTS_FILE.with_suffix(".tmp")
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(rows, file, indent=2)
        temp_file.replace(PAYMENTS_FILE)
    except OSError as exc:
        raise StorageError(f"Failed to write payments store: {exc}") from exc


def list_payments() -> list[dict[str, Any]]:
    with _LOCK:
        return _load_rows()


def get_payment(payment_id: str) -> dict[str, Any] | None:
    rows = list_payments()
    for row in rows:
        if row.get("payment_id") == payment_id:
            return row
    return None


def list_payments_by_invoice(invoice_id: str) -> list[dict[str, Any]]:
    rows = list_payments()
    return [row for row in rows if row.get("invoice_id") == invoice_id]


def _next_payment_id(rows: list[dict[str, Any]]) -> str:
    max_seen = 0
    for row in rows:
        payment_id = str(row.get("payment_id", ""))
        if payment_id.startswith("PAY-"):
            suffix = payment_id.removeprefix("PAY-")
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
    return f"PAY-{max_seen + 1:04d}"


def create_payment(invoice_id: str, paid: int) -> dict[str, Any]:
    with _LOCK:
        rows = _load_rows()
        record = {"payment_id": _next_payment_id(rows), "invoice_id": invoice_id, "paid": paid}
        rows.append(record)
        _save_rows(rows)
    return record


def upsert_payment(payment_id: str, invoice_id: str, paid: int) -> tuple[dict[str, Any], bool]:
    with _LOCK:
        rows = _load_rows()
        record = {"payment_id": payment_id, "invoice_id": invoice_id, "paid": paid}
        for idx, row in enumerate(rows):
            if row.get("payment_id") == payment_id:
                rows[idx] = record
                _save_rows(rows)
                return record, False
        rows.append(record)
        _save_rows(rows)
        return record, True


def delete_payment(payment_id: str) -> bool:
    with _LOCK:
        rows = _load_rows()
        kept_rows = [row for row in rows if row.get("payment_id") != payment_id]
        if len(kept_rows) == len(rows):
            return False
        _save_rows(kept_rows)
        return True

