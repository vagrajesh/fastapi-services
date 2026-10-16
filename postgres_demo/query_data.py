"""Query existing payments."""
from db_connection import get_connection


def get_all_payments(limit: int = 100) -> list[tuple]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT payment_id, vendor, amount, status, approval "
            "FROM payments ORDER BY payment_id LIMIT %s",
            (limit,),
        ).fetchall()


def get_payment(payment_id: str) -> tuple | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT payment_id, vendor, amount, status, approval "
            "FROM payments WHERE payment_id = %s",
            (payment_id,),
        ).fetchone()


if __name__ == "__main__":
    for row in get_all_payments(10):
        print(row)
    print("P001 ->", get_payment("P001"))
