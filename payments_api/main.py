from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse

from .models import ErrorResponse, PaymentCreate, PaymentRecord, PaymentUpdate
from .repository import StorageError
from .services import NotFoundError
from . import services

app = FastAPI(title="Standalone Payments API", version="1.0.0")


@app.exception_handler(StorageError)
async def handle_storage_error(_, exc: StorageError):
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)})


@app.get("/payments", response_model=list[PaymentRecord], tags=["payments"])
def get_payments() -> list[PaymentRecord]:
    return services.list_payments()


@app.get(
    "/payments/{payment_id}",
    response_model=PaymentRecord,
    responses={404: {"model": ErrorResponse}},
    tags=["payments"],
)
def get_payment_by_id(payment_id: str) -> PaymentRecord:
    try:
        return services.get_payment(payment_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/payments/by-invoice/{invoice_id}", response_model=list[PaymentRecord], tags=["payments"])
def get_payments_for_invoice(invoice_id: str) -> list[PaymentRecord]:
    return services.list_payments_by_invoice(invoice_id)


@app.post(
    "/payments",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentRecord,
    responses={422: {"model": ErrorResponse}},
    tags=["payments"],
)
def post_payment(payload: PaymentCreate) -> PaymentRecord:
    return services.create_payment(payload)


@app.put(
    "/payments/{payment_id}",
    response_model=PaymentRecord,
    responses={200: {"model": PaymentRecord}, 201: {"model": PaymentRecord}},
    tags=["payments"],
)
def put_payment(payment_id: str, payload: PaymentUpdate, response: Response) -> PaymentRecord:
    record, created = services.upsert_payment(payment_id, payload)
    if created:
        response.status_code = status.HTTP_201_CREATED
    return record


@app.delete(
    "/payments/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
    tags=["payments"],
)
def delete_payment(payment_id: str) -> Response:
    try:
        services.delete_payment(payment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/reconciliation/report", tags=["reconciliation"])
def get_reconciliation_report() -> dict:
    return services.get_reconciliation_report()
