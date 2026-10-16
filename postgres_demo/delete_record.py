"""Delete a specific payment record."""
from db_connection import get_connection


def delete_payment(payment_id: str) -> bool:
    """Return True if a row was deleted, False if payment_id doesn't exist."""
    with get_connection() as conn:  # commits on success, rolls back on error
        cur = conn.execute(
            "DELETE FROM payments WHERE payment_id = %s", (payment_id,)
        )
        return cur.rowcount == 1


if __name__ == "__main__":
    if delete_payment("P100"):
        print("P100 deleted")
    else:
        print("P100 not found")
