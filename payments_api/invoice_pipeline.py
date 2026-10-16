from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from typing import Any

RAW_INVOICES = [
    {"invoice_id": "INV-101", "vendor": "ABC Ltd", "amount": 85000, "status": "PENDING", "date": "2026-09-03"},
    {"invoice_id": "INV-102", "vendor": "xyz corp", "amount": 142500, "status": "pending", "date": "2026-09-05"},
    {"invoice_id": "INV-101", "vendor": "ABC Ltd", "amount": 85000, "status": "PENDING", "date": "2026-09-03"},
    {"invoice_id": "INV-103", "vendor": "Globex", "amount": -550000, "status": "PENDING", "date": "2026-09-07"},
    {"invoice_id": "INV-104", "vendor": "ABC Ltd ", "amount": 62000, "status": "PAID", "date": "2026-09-08"},
    {"invoice_id": "INV-102", "vendor": "XYZ Corp", "amount": 150000, "status": "PENDING", "date": "2026-09-12"},
    {"invoice_id": "INV-105", "vendor": "Globex", "amount": 550000, "status": "PENDING", "date": "2026-09-09"},
    {"invoice_id": "INV-106", "vendor": "Initech", "amount": None, "status": "PENDING", "date": "2026-09-15"},
    {"invoice_id": "INV-107", "vendor": "ABC Ltd", "amount": 85000, "status": "PENDING", "date": "2026-09-03"},
]

RAW_PAYMENTS = [
    {"invoice_id": "INV-101", "paid": 85000},
    {"invoice_id": "INV-101", "paid": 85000},
    {"invoice_id": "INV-104", "paid": 60000},
    {"invoice_id": "INV-109", "paid": 12000},
]


def normalize_invoices(invoices: list[dict[str, Any]]) -> list[int]:
    none_amount_indexes: list[int] = []
    for idx, row in enumerate(invoices):
        row["vendor"] = str(row.get("vendor", "")).strip().title()
        row["status"] = str(row.get("status", "")).upper()
        if row.get("amount") is None:
            none_amount_indexes.append(idx)
    return none_amount_indexes


def remove_exact_duplicates(invoices: list[dict[str, Any]]) -> dict[tuple[Any, ...], list[int]]:
    key_to_indexes: dict[tuple[Any, ...], list[int]] = {}
    for idx, row in enumerate(invoices):
        row_key = (
            row.get("invoice_id"),
            row.get("vendor"),
            row.get("amount"),
            row.get("status"),
            row.get("date"),
        )
        key_to_indexes.setdefault(row_key, []).append(idx)

    exact_dupes = {key: indexes for key, indexes in key_to_indexes.items() if len(indexes) > 1}
    indexes_to_remove = sorted((idx for indexes in exact_dupes.values() for idx in indexes[1:]), reverse=True)
    for idx in indexes_to_remove:
        invoices.pop(idx)
    return exact_dupes


def find_suspected_duplicates(invoices: list[dict[str, Any]]) -> list[tuple[str, str]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in invoices:
        if row.get("amount") is None:
            continue
        grouped[(row.get("vendor"), row.get("amount"), row.get("date"))].append(row)

    suspected_pairs: list[tuple[str, str]] = []
    for rows in grouped.values():
        ids = list(dict.fromkeys(str(row.get("invoice_id")) for row in rows))
        if len(ids) < 2:
            continue
        for left, right in combinations(ids, 2):
            suspected_pairs.append((left, right))
    return suspected_pairs


def apply_credit_notes(invoices: list[dict[str, Any]]) -> tuple[list[tuple[int, int]], list[int]]:
    matched_pairs: list[tuple[int, int]] = []
    unmatched_credits: list[int] = []
    consumed_positive_indexes: set[int] = set()

    for neg_idx, row in enumerate(invoices):
        amount = row.get("amount")
        if not isinstance(amount, (int, float)) or amount >= 0:
            continue

        partner_idx = None
        for pos_idx in range(neg_idx - 1, -1, -1):
            candidate = invoices[pos_idx]
            candidate_amount = candidate.get("amount")
            if (
                isinstance(candidate_amount, (int, float))
                and candidate_amount > 0
                and candidate.get("vendor") == row.get("vendor")
                and candidate_amount == abs(amount)
                and pos_idx not in consumed_positive_indexes
            ):
                partner_idx = pos_idx
                break

        if partner_idx is None:
            unmatched_credits.append(neg_idx)
            continue

        consumed_positive_indexes.add(partner_idx)
        invoices[partner_idx]["status"] = "CANCELLED"
        invoices[neg_idx]["status"] = "CANCELLED"
        matched_pairs.append((partner_idx, neg_idx))

    return matched_pairs, unmatched_credits


def reconcile_payments(
    invoices: list[dict[str, Any]],
    payments: list[dict[str, Any]],
    none_amount_indexes: set[int],
) -> dict[str, Any]:
    payment_totals: dict[str, int] = defaultdict(int)
    for payment in payments:
        payment_totals[str(payment.get("invoice_id"))] += int(payment.get("paid", 0))

    known_invoice_ids = {str(row.get("invoice_id")) for row in invoices}
    unmatched_payments = [payment for payment in payments if str(payment.get("invoice_id")) not in known_invoice_ids]

    reconciliation_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(invoices):
        amount = row.get("amount")
        if idx in none_amount_indexes or row.get("status") == "CANCELLED":
            continue
        if not isinstance(amount, (int, float)):
            continue

        invoice_id = str(row.get("invoice_id"))
        total_paid = payment_totals.get(invoice_id, 0)
        reconciliation_rows.append(
            {
                "index": idx,
                "invoice_id": invoice_id,
                "invoice_amount": int(amount),
                "total_paid": total_paid,
                "balance": int(amount) - total_paid,
                "status": row.get("status"),
            }
        )

    return {"rows": reconciliation_rows, "unmatched_payments": unmatched_payments}


def run_all_phases(
    invoices: list[dict[str, Any]] | None = None,
    payments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    working_invoices = deepcopy(invoices if invoices is not None else RAW_INVOICES)
    working_payments = deepcopy(payments if payments is not None else RAW_PAYMENTS)

    none_amount_indexes = normalize_invoices(working_invoices)
    exact_dupes = remove_exact_duplicates(working_invoices)
    suspected_dupes = find_suspected_duplicates(working_invoices)
    matched_credit_pairs, unmatched_credit_indexes = apply_credit_notes(working_invoices)
    reconciliation = reconcile_payments(working_invoices, working_payments, set(none_amount_indexes))

    return {
        "normalized_invoices": working_invoices,
        "none_amount_indexes": none_amount_indexes,
        "exact_dupes": exact_dupes,
        "suspected_dupes": suspected_dupes,
        "matched_credit_pairs": matched_credit_pairs,
        "unmatched_credit_indexes": unmatched_credit_indexes,
        "reconciliation": reconciliation,
    }

