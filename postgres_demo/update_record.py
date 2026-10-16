"""Update one payment record."""
from db_connection import get_connection


def update_payment_status(payment_id: str, status: str) -> bool:
    """Return True if a row was updated, False if payment_id doesn't exist."""
    with get_connection() as conn:  # commits on success, rolls back on error
        cur = conn.execute(
            "UPDATE payments SET status = %s WHERE payment_id = %s",
            (status, payment_id),
        )
        return cur.rowcount == 1


if __name__ == "__main__":
    if update_payment_status("P001", "Paid"):
        print("P001 updated to Paid")
    else:
        print("P001 not found")
