# Service Layer Workflow

## Purpose

Use this guide to create or review a Python `services.py` module that coordinates a model and its repository. A service owns domain operations, model construction/validation, and service-level errors. It should not perform file I/O directly or decide HTTP status codes.

The inspected `services.py` is an invoice service paired with `model.py` and `repository.py`. Treat `Invoice`, invoice IDs, and the function names below as examples. For future work, discover the actual model and repository for the entity before implementing service logic.

## When to Use

- Adding service functions between API routes and a model/repository.
- Reviewing create, get, update, or delete behavior.
- Making persistence operations return validated model instances.
- Deciding where not-found, duplicate, and validation errors belong.

## Workflow

1. Read the entity's model, repository, API route, and existing service module. Identify the model fields, Pydantic major version, repository function signatures/return values, route-level error mappings, and current public service API.
2. Use one service module per coherent entity/domain service when that matches existing project structure. Do not blindly create a separate service for every request/response model variant if those models represent operations on the same persisted entity.
3. Import the actual repository and model. If a module filename is not a valid Python identifier (for example, `01_model.py`), use the project's established dynamic import pattern or rename/restructure only with approval because import names may be public project conventions.
4. Define explicit input and output types consistent with the contract. Validate data by constructing the correct model before persisting or returning it. Preserve the installed Pydantic version's validation semantics.
5. For reads, fetch from the repository, translate a missing record into the service's established not-found exception, then validate persisted data using the model before returning.
6. For creates, decide which fields are client-supplied and which are service-generated. Build a fresh input mapping, set generated fields deliberately, construct the model, check any required uniqueness rule, persist through the repository, and return the model.
7. For updates, decide whether the API means full replacement or partial update. For partial update, merge existing values with submitted changes and explicitly protect immutable identifiers. Construct/validate the result before writing.
8. For deletes, coordinate existence checking and repository deletion. Check and handle the repository's actual return value where the contract requires it; do not assume a preceding lookup guarantees deletion succeeded if concurrent changes are possible.
9. Raise domain/service exceptions rather than HTTP exceptions. Let the API layer map those exceptions to appropriate HTTP responses.
10. Keep repository failures and Pydantic validation errors observable. Do not catch broad exceptions or turn failures into success-shaped return values.
11. Test normal, missing, duplicate, invalid, and persistence-failure cases using the real repository contract or a focused test double. Verify generated IDs, merge precedence, return models, and repository calls.

## Service Responsibilities and Boundaries

- **Model:** Defines the entity's data shape and validation.
- **Repository:** Loads and writes persistent records and reports persistence-level outcomes.
- **Service:** Coordinates model validation with repository operations and enforces domain operation rules.
- **API route:** Parses HTTP input and maps service errors to HTTP status codes and response formats.
- A service should not open JSON files, issue SQL, or call HTTP response constructors directly.
- A service should not duplicate model validation rules as unrelated manual checks. Rely on the model unless a separate business rule is required.
- A Python `ValueError` may be used when consistent with the project, but dedicated domain exceptions can communicate not-found, duplicate, and conflict cases more clearly. Do not change exception types without considering API callers.

## Model-to-Service Mapping

Before implementation, map each model family to its service and repository:

| Model family | Service module (example) | Repository module (example) | Questions to resolve |
|---|---|---|---|
| `Invoice` | `invoice_service.py` or project-standard `services.py` | `invoice_repository.py` | Is the ID generated? What fields can be updated? |
| `Payment` | `payment_service.py` or project-standard `services.py` | `payment_repository.py` | What uniquely identifies a payment? Can an invoice have several payments? |

The current `day3/refactor/03_services.py` coordinates only `Invoice` and the invoice repository. A `Payment` service should use payment-specific models and repository functions; do not reuse invoice lookups or assume a payment's `invoice_id` is its unique key.

## Walkthrough of `day3/refactor/03_services.py`

This section accounts for every nonblank source line in the supplied 31-line module. Blank lines only separate sections and have no runtime behavior.

### Imports and dependencies

- `import importlib #// Import the importlib module to dynamically import other modules`: imports Python's dynamic import utility. The inline comment explains intent but is not executable.
- `rep = importlib.import_module("04_repository") #// Import the repository module for invoice data operations`: imports the module named `04_repository` and stores it in the local alias `rep`. This works with the numeric filename, which cannot be imported using ordinary `import 04_repository` syntax. It depends on the module being resolvable on the Python import path.
- `Invoice = importlib.import_module("01_model").Invoice #// Import the Invoice model class from the model module`: imports `01_model` dynamically and binds its `Invoice` class to `Invoice`. Import-time failures propagate; there is no fallback.

### `get_invoice_by_id`

- `def get_invoice_by_id(invoice_id: str) -> Invoice: ...`: declares a typed service function taking a string ID and documenting an `Invoice` return. Type annotations do not themselves validate runtime inputs or outputs.
- `invoice = rep.get_invoice_by_id(invoice_id) ...`: delegates lookup to the repository; the service does not read persistence directly.
- `if invoice is None: ...`: treats exactly `None` as not found. Other false-like values are not considered missing.
- `raise ValueError(f"Invoice with ID {invoice_id} not found") ...`: raises a service-level error containing the requested ID. The API route is responsible for mapping it to an HTTP response.
- `return Invoice(**invoice) ...`: constructs an `Invoice` from the persisted mapping, validating the data according to the model/Pydantic version, then returns the model object.

### `create_invoice`

- `def create_invoice(invoice: dict) -> Invoice: ...`: declares a create operation that accepts a dictionary and returns the validated model. The annotation does not enforce the dictionary's keys at runtime.
- `invoice_data = {**invoice, "invoice_id": rep.get_next_invoice_id()}`: creates a new shallow mapping from the caller's mapping, then assigns the generated ID. Because the generated entry comes last, it overrides any `invoice_id` supplied by the caller. Nested values are not copied.
- `new_invoice = Invoice(**invoice_data)`: validates/constructs the full model before any repository write. A model validation failure propagates and prevents persistence.
- `if rep.get_invoice_by_id(new_invoice.invoice_id) is not None: ...`: checks whether the generated ID is already present. This detects an existing collision at check time, not concurrent races between check and insertion.
- `raise ValueError(f"Invoice with ID {new_invoice.invoice_id} already exists") ...`: reports the collision using the service-level exception. The route may map this to a conflict response.
- `rep.add_invoice(new_invoice) ...`: persists the model through the repository. In the inspected repository, `add_invoice` converts model values to a dictionary; persistence exceptions propagate.
- `return new_invoice ...`: returns the same validated model instance after persistence. The function does not return a repository-generated result.

### `update_invoice`

- `def update_invoice(invoice_id: str, invoice_data: dict) -> Invoice: ...`: declares an update operation keyed by a string ID. Its behavior below is a partial update implemented as a full-model replacement after merging.
- `existing_invoice = rep.get_invoice_by_id(invoice_id) ...`: retrieves the existing record as a dictionary or `None`.
- `if existing_invoice is None: ...`: detects a missing record before constructing an update.
- `raise ValueError(f"Invoice with ID {invoice_id} not found") ...`: reports absence as a service-level error; the API decides its HTTP mapping.
- `updated_invoice = Invoice(**{**existing_invoice, **invoice_data, "invoice_id": invoice_id}) ...`: makes a new merged mapping and validates it as a complete `Invoice`. Merge order is significant: existing values are copied first, submitted values override matching fields, and the path ID overrides submitted IDs last. Thus omitted fields are preserved and the record key cannot be changed by the request.
- `rep.update_invoice(invoice_id, updated_invoice) ...`: delegates replacement to the repository. In the inspected repository, update returns `True` or `False`, but this service ignores that result. A concurrent deletion or other miss after the earlier lookup could therefore be reported as successful.
- `return updated_invoice ...`: returns the validated model regardless of the repository Boolean result. Preserve this only when reproducing existing behavior; for robust concurrent operation, check the Boolean and report a failure according to the service contract.

### `delete_invoice`

- `def delete_invoice(invoice_id: str) -> None: ...`: declares deletion and documents no return value.
- `if rep.get_invoice_by_id(invoice_id) is None: ...`: performs a pre-delete existence lookup. This introduces two repository operations and does not make them atomic.
- `raise ValueError(f"Invoice with ID {invoice_id} not found") ...`: reports a missing invoice to the caller for API-level mapping.
- `rep.delete_invoice(invoice_id) ...`: delegates deletion to the repository. The inspected repository returns a Boolean, which this service ignores; if the record disappears after the existence check, the service still completes without signaling the failed delete.
- The function has no explicit `return`, so Python returns `None` on successful completion, matching its annotation.

## Adaptation Rules

- Replace invoice-specific function names, model classes, identifiers, and repository calls with those of the target entity. Keep names consistent with the public API and project conventions.
- Confirm a stable unique key for every entity. A relationship field is not automatically unique.
- Preserve merge precedence intentionally. For partial updates, generally use existing data < submitted changes < immutable path/key values. For full replacement, do not accidentally preserve omitted old values.
- Decide whether generated IDs are trusted, collision-checked, or reserved atomically. A read-then-check-then-write sequence is vulnerable to concurrency races.
- Decide whether the service or repository owns generated IDs; do not generate them in both layers.
- Check repository return values when they communicate whether an update or delete actually occurred. Ignore them only when the contract intentionally says so.
- Keep service errors distinct from validation and storage errors. Do not catch `ValueError` broadly if that would disguise unrelated errors; use explicit exception types and boundaries where needed.
- Dynamic imports are a workaround for the numeric module names in this example, not a requirement for new projects. Prefer ordinary package imports with valid identifiers when compatible with project structure.
- Consider circular dependencies: routes may depend on services, services on repositories and models, but lower layers should not import the route layer.
- Do not expose storage dictionaries when the service contract promises model instances; validate them at the intended boundary.

## Completion Checks

- The service imports the correct model and repository for its entity.
- No persistence I/O occurs directly in the service.
- Reads return validated model instances and missing records produce the documented service exception.
- Creates apply server-generated fields in the intended precedence, validate before writing, and handle uniqueness according to the contract.
- Updates implement the intended partial or full replacement semantics, preserve immutable IDs, validate before writing, and handle repository failure results.
- Deletes distinguish a missing record from a failed persistence operation as required.
- API routes—not service functions—translate domain/service errors into HTTP responses.
- Tests cover success paths, missing IDs, invalid model data, duplicate/generated IDs, update merge precedence, deletion outcomes, and repository exceptions.
