from __future__ import annotations

from .invoice_pipeline import run_all_phases


def main() -> None:
    result = run_all_phases()

    print("Phase 1 - Normalize")
    for idx in result["none_amount_indexes"]:
        print(f"amount is None at index {idx}")

    print("\nPhase 2 - Exact duplicates")
    for key, indexes in result["exact_dupes"].items():
        print(f"{key} -> {indexes}")

    print("\nPhase 3 - Suspected duplicates")
    for left, right in result["suspected_dupes"]:
        print(f"({left} ~ {right})")

    print("\nPhase 4 - Credit notes")
    for left_idx, right_idx in result["matched_credit_pairs"]:
        print(f"{left_idx} <-> {right_idx}")
    for idx in result["unmatched_credit_indexes"]:
        print(f"Unmatched credit note at index {idx}")

    print("\nPhase 5 - Reconcile payments")
    for row in result["reconciliation"]["rows"]:
        print(
            f"{row['invoice_id']}: amount={row['invoice_amount']}, paid={row['total_paid']}, "
            f"balance={row['balance']}, status={row['status']}"
        )
    for payment in result["reconciliation"]["unmatched_payments"]:
        print(f"Unmatched payment: {payment}")

    print("\nBuild API for payments - GET, POST, DELETE, UPDATE")


if __name__ == "__main__":
    main()

