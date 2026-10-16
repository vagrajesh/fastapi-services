# FastAPI Application Entry-Point Workflow

## Purpose

Use this guide to create or review a FastAPI entry-point module (often `main.py`) that connects HTTP routes to a model and a service layer. The reviewed file, `main.py`, is an invoice API example. Treat invoice names, URL paths, fields, and status mappings as examples, and use the target project's actual model, service, and API contract.

## When to Use

- Creating a FastAPI application entry point and CRUD routes.
- Wiring request/response schemas to service functions.
- Reviewing HTTP error mapping and route behavior.
- Understanding how route, service, model, and repository layers work together.

## Application Layer Responsibilities

- **Model/schema:** Defines data fields and validation. Use request models for incoming data and response models for output where appropriate.
- **Repository:** Loads and saves persisted records. It should not know about FastAPI or HTTP status codes.
- **Service:** Coordinates model validation and repository operations, applies domain rules, and raises documented domain/service errors.
- **API route / application entry point:** Defines HTTP methods and paths, parses requests, invokes services, declares response behavior, and maps service errors to HTTP responses.
- Keep imports flowing from the API layer down to services and models/repositories. Lower layers should not import the route module.

## Workflow

1. Read the existing model, repository, service module, route module, and dependency configuration. Confirm their import paths, function signatures, Pydantic version, response behavior, and error contracts.
2. Decide the application entry-point location and preserve the project's package/import conventions. If modules have numeric names such as `model.py`, follow the existing dynamic import pattern only where necessary; for new modules prefer valid Python identifiers.
3. Create or reuse one `FastAPI` app instance. Do not accidentally create multiple application instances when registering routes.
4. For each operation, choose the HTTP method, URL path, input schema, response schema, and status behavior from the API contract.
5. Prefer explicit Pydantic request models over bare `dict` parameters when the request shape is known. Use the intended create/update schemas and define partial versus full update semantics deliberately.
6. Declare response models that match the service return type. For operations with no response body, define the intended status code and response behavior explicitly.
7. Call the service from each route; do not call repository functions directly or perform persistence in a route.
8. Catch only documented service exceptions and map each to an appropriate HTTP status. Do not map every `ValueError` to one status if that could misclassify validation, not-found, duplicate, or unrelated errors.
9. Keep error details safe and useful. Return expected client-facing messages, but do not expose internal paths, stack traces, or sensitive values.
10. Test route success and error behavior with the project's test client or integration test setup, including request validation, response serialization, and service-to-HTTP mappings.

## Model-to-API Wiring

Before implementing routes, map the entity contract:

| Concern | Invoice example from the inspected files | General rule |
|---|---|---|
| Model | `model` | Use the model/schema belonging to this entity. |
| Repository | `repository` | Routes should not call it directly. |
| Service | `services` | Routes delegate application/domain operations here. |
| Read route | `GET /invoices/{invoice_id}` | Return a validated entity response or mapped not-found error. |
| Create route | `POST /invoices` | Validate an explicit create request and return the created entity. |
| Update route | `PUT /invoices/{invoice_id}` | Match full-replacement or partial-update semantics explicitly. |
| Delete route | `DELETE /invoices/{invoice_id}` | Define whether success has no body and select its status code. |

For another entity, such as a payment, use that entity's own request/response models and service functions. Do not assume its key is `invoice_id` or reuse invoice operations merely because a payment references an invoice.

## Walkthrough of `day3/refactor/02_main.py`

The notes below cover each nonblank source line. Blank lines only separate imports, app setup, and route definitions.

### Imports and application wiring

- `from fastapi import FastAPI, HTTPException`: imports the FastAPI application class and exception used to produce HTTP error responses. Importing `HTTPException` in the route layer is appropriate; repository and service modules should not depend on it.
- `from importlib import import_module`: imports the dynamic module loader used for filenames that begin with digits.
- `Invoice = import_module("01_model").Invoice`: loads the `Invoice` class from `01_model.py` and binds it locally. This relies on the module being on Python's import path and can fail at application import/startup if it is not found. A package module with a valid identifier would normally use a regular import.
- `_services = import_module("03_services")`: dynamically loads the service module and stores its module object. The underscore signals a private local name by convention; it is not access control.
- `get_invoice_by_id = _services.get_invoice_by_id`: binds the service lookup function into the API module's namespace. This is a direct alias, not a wrapper.
- `create_invoice = _services.create_invoice`: binds the service create function for route use.
- `update_invoice = _services.update_invoice`: binds the service update function for route use.
- `delete_invoice = _services.delete_invoice`: binds the service delete function for route use.
- `app = FastAPI()`: creates the ASGI application instance that registers routes and is served by the selected ASGI server.

### Read route

- `@app.get("/invoices/{invoice_id}", response_model=Invoice)`: registers the following function as a GET endpoint with a path parameter. FastAPI uses `Invoice` as the documented/serialized response contract and validates or serializes the returned value accordingly.
- `def read_invoice(invoice_id: str):`: defines the route handler and declares the path parameter as a string. The annotation is used by FastAPI for parameter processing/schema generation; use explicit schemas for complex request bodies.
- `try:`: begins a block for translating a selected service failure into an HTTP error.
- `return get_invoice_by_id(invoice_id)`: delegates to the service and returns its result. In the supplied service, a found record is reconstructed as an `Invoice` model.
- `except ValueError as e:`: catches `ValueError` raised anywhere within the called service path. This can be broader than intended: model validation errors may also be ValueError-compatible, depending on the Pydantic version, so invalid persisted data could be mislabeled as not found.
- `raise HTTPException(status_code=404, detail=str(e))`: turns the caught error into HTTP 404 and uses its text as the response detail. Prefer a dedicated not-found exception or a narrowly scoped mapping so unrelated failures are not returned as 404.

### Create route

- `@app.post("/invoices", response_model=Invoice)`: registers a POST endpoint and declares that a successful response is an `Invoice`.
- `def create_new_invoice(invoice: dict):`: accepts a generic dictionary request body. This does not define field-level request validation or a precise OpenAPI schema. Prefer a dedicated create input model when the contract is known.
- `try:`: begins the error-translation block for service creation.
- `return create_invoice(invoice)`: passes the parsed dictionary to the service and returns the created result. The service generates the ID, constructs the `Invoice`, checks for an existing generated ID, persists it, and returns the model.
- `except ValueError as e:`: catches all `ValueError`-compatible exceptions from the service. Since model construction can fail validation, this may classify invalid request fields as conflict instead of as request validation errors.
- `raise HTTPException(status_code=409, detail=str(e))`: maps the caught error to HTTP 409. This is suitable for a documented duplicate/conflict condition, but should not be used for validation errors or arbitrary `ValueError`s.

### Update route

- `@app.put("/invoices/{invoice_id}", response_model=Invoice)`: registers a PUT endpoint keyed by a path parameter and documents an `Invoice` response. PUT conventionally indicates replacement; the current service merges submitted fields into the stored object, which behaves more like a partial update. Align method/schema/service behavior or use PATCH if that matches the contract.
- `def update_existing_invoice(invoice_id: str, invoice_data: dict):`: accepts a string path key and generic dictionary body. The dictionary has no explicit field validation or schema documentation.
- `try:`: starts the service-error translation block.
- `return update_invoice(invoice_id, invoice_data)`: delegates to the service. The current service preserves omitted existing values, applies supplied values, and forces `invoice_id` to the path value.
- `except ValueError as e:`: catches `ValueError`-compatible failures. This may mislabel validation errors as not found; prefer a dedicated not-found exception.
- `raise HTTPException(status_code=404, detail=str(e))`: maps every caught `ValueError` to 404. This only accurately represents the intended missing-invoice error if other ValueErrors cannot escape this service operation.

### Delete route

- `@app.delete("/invoices/{invoice_id}", response_model=None)`: registers a DELETE route and indicates there is no declared Pydantic response model. It does not by itself make the response status code 204.
- `def delete_existing_invoice(invoice_id: str):`: defines the handler with a string path identifier. No return annotation is supplied.
- `try:`: begins error handling for the delete operation.
- `delete_invoice(invoice_id)`: invokes the service and discards its return. The service annotation is `None`; the repository's Boolean deletion result is also ignored by the service.
- `except ValueError as e:`: catches service `ValueError`s, potentially including errors broader than not-found.
- `raise HTTPException(status_code=404, detail=str(e))`: maps the selected error to 404. Choose explicit exception types and status codes so storage failures and validation failures are not misreported.
- The handler has no explicit success return, so it returns `None`. With no explicit 204 status, clients generally receive a successful response with the framework's default status and a null/empty body representation. Declare the intended success status explicitly if the API contract requires 204 No Content.

## Recommended Generic Skeleton

This is a structural illustration, not a drop-in implementation. Replace example imports, schemas, service names, paths, and exception types with the project's actual public interfaces.

```python
from fastapi import FastAPI, HTTPException  # Imports the framework app and HTTP error response type.
from project.models import Item  # Imports the entity response schema.
from project.services import item_service  # Imports the service boundary used by route handlers.
from project.services.errors import ItemNotFoundError  # Imports the service exception mapped to HTTP 404.

app = FastAPI()  # Creates the ASGI app instance for server startup.

@app.get("/items/{item_id}", response_model=Item)  # Registers a read endpoint with a declared response schema.
def read_item(item_id: str) -> Item:  # Declares the handler's path input and returned entity type.
    try:  # Starts translation of the documented service not-found error.
        return item_service.get_item_by_id(item_id)  # Delegates lookup and domain handling to the service.
    except ItemNotFoundError as error:  # Catches only the expected not-found condition.
        raise HTTPException(status_code=404, detail=str(error)) from error  # Converts that condition into HTTP 404.
```

## Adaptation and Reliability Rules

- Prefer explicit request models (for example `ItemCreate` and `ItemUpdate`) over `dict` so required fields, types, validation, and API documentation are clear.
- Separate request schemas from response/entity schemas when create/update requirements differ from persisted data. Do not accept server-owned identifiers or fields just because they exist on the response model.
- Keep response models aligned with service outputs and prevent accidental exposure of internal fields.
- Use dedicated exceptions such as `ItemNotFoundError` and `DuplicateItemError` when one generic exception would make status mapping ambiguous.
- Avoid catching broad built-in exceptions around an entire service call. A `ValueError` can mean a missing record in one path and invalid model data in another.
- Avoid exposing raw exception details without considering whether they contain internal or sensitive information.
- Specify status behavior deliberately. A successful DELETE may return 204 with no content or 200 with a response body; implement the contract explicitly.
- Ensure route methods and service behavior agree: PUT is generally full replacement, while PATCH commonly expresses partial updates.
- Use one canonical service import per entity. Direct aliases are acceptable for a small module, but a service namespace can make ownership clearer in larger applications.
- Keep dynamic imports only when needed for current module naming. Renaming numbered modules can improve normal imports but may affect scripts and callers, so do not rename them silently.
- Test through FastAPI's test client as well as testing the service independently. Route tests verify parsing, response serialization, OpenAPI shape, status codes, and error mapping.

## Completion Checks

- The app imports successfully, and all referenced model/service modules and names resolve.
- Each route uses the correct HTTP method, path, request schema, response schema, and status behavior.
- Routes delegate to services and contain no repository or filesystem logic.
- Request validation errors retain the framework's appropriate client-error behavior.
- Not-found, duplicate, and other documented service errors map to distinct, intended HTTP statuses.
- Successful read/create/update responses serialize to the declared model; delete response matches its declared status/body contract.
- Tests cover valid requests, invalid request bodies, missing identifiers, duplicate/conflict cases, and service/persistence failures.
