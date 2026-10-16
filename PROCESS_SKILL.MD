# FastAPI Service Development Process

## Purpose

Use this process to build or review a FastAPI service in coordinated layers: model/schema, repository, service logic, and API entry point. It composes the guidance in:

- [MODEL_SKILL.MD](./MODEL_SKILL.MD)
- [REPOSITORY_SKILL.MD](./REPOSITORY_SKILL.MD)
- [SERVICES_SKILL.MD](./SERVICES_SKILL.MD)
- [MAIN_SKILL.MD](./MAIN_SKILL.MD)

Follow each guide for its layer-specific details. This document defines the order of work, the contracts passed between layers, and end-to-end validation. Examples in the referenced documents are illustrative; use the target project's actual entities, naming, persistence system, API behavior, and dependency versions.

## When to Use

- Building a new FastAPI CRUD service for a model.
- Adding an entity to a project with existing models, repositories, services, and routes.
- Reviewing whether all application layers agree on the same data and error contracts.
- Extending a JSON-backed example to another model family.

## Layer Responsibilities

| Layer | Owns | Must not own |
|---|---|---|
| Model/schema | Field types, requiredness, defaults, constraints explicitly in the contract, validation, serialization contract | File/database I/O, HTTP status selection |
| Repository | Storage paths/configuration, persistence, serialization to/from storage, record lookup and mutation | HTTP routing, request parsing, business workflows |
| Service | Coordination of model and repository, domain operation rules, generated values, domain/service errors | Direct storage I/O, HTTP exceptions/status codes |
| FastAPI routes (`main.py`) | App setup, HTTP methods/paths, request and response schemas, invocation of services, HTTP error mapping | Direct repository calls, persistence logic, duplicated domain validation |

Dependencies should flow from routes to services, then to models/repositories. Lower-level model and repository modules must not import route code. Avoid circular imports.

## End-to-End Workflow

### Phase 1: Discover and define scope

1. Identify the requested entity, operations, and API behavior. Determine which files are in scope and whether this is a new service or an extension.
2. Inspect the existing model(s), repository/repositories, service module(s), route/app entry point, tests, and dependency files before editing.
3. Record the actual imports, public function names/signatures, identifier fields, persistence format, Pydantic version, API paths/methods, response schemas, and exception/status mappings.
4. Search for existing implementations to reuse. Do not create duplicate models, repositories, services, or app instances.
5. Ask for clarification rather than inventing a contract when a key decision blocks safe implementation—for example, whether an update is partial or full replacement, or how a payment is uniquely identified.

### Phase 2: Establish the entity contract

Create a compact contract table before implementation:

| Contract item | Decision to record |
|---|---|
| Entity and model module | Canonical model/schema name and import path |
| Fields | Name, type, required/optional status, defaults, aliases, constraints |
| Stable key | Unique identifier and whether/how it is generated |
| Operations | Create, read, list, update, delete behavior required |
| Update semantics | Full replacement or partial update; immutable fields |
| Storage | Repository module, backend, key, record shape, failure behavior |
| API | Path, HTTP method, request schema, response schema, success status |
| Errors | Not-found, duplicate/conflict, validation, and persistence failures |

Do not treat sample values or names in the guides as requirements. In particular, a foreign key such as `payment.invoice_id` is not necessarily a unique payment identifier.

### Phase 3: Define or adapt models

1. Follow [MODEL_SKILL.MD](./MODEL_SKILL.MD) to verify the installed Pydantic major version and existing project conventions.
2. Reuse an existing model if it represents the same contract. Do not introduce competing definitions for one entity.
3. Define separate request/response schemas only where their fields or validation differ, such as server-generated identifiers or partial updates.
4. Keep requiredness, defaults, aliases, and validation rules contract-driven. Do not add assumed business constraints.
5. Confirm the model imports and validate representative accepted and rejected inputs before wiring persistence.
6. Follow the model guide's code-comment expectations when creating or materially changing model code.

**Gate:** Do not proceed with an unresolved Pydantic version, unclear field contract, or conflicting existing model. Report the uncertainty and obtain the needed decision.

### Phase 4: Implement repository persistence

1. Follow [REPOSITORY_SKILL.MD](./REPOSITORY_SKILL.MD) to map the model family to its repository module, storage backend/file, and stable record key.
2. Implement only the persistence operations the service needs. Keep repository names and return values explicit and consistent.
3. For JSON storage, decide the top-level document shape, path, encoding, missing-file behavior, and write strategy. Do not silently convert malformed data or I/O failures into an empty successful result.
4. Ensure model instances are serialized using the project's Pydantic version and supported storage representation.
5. Define duplicate and not-found behavior, including whether methods return `None`/Boolean values or raise repository-level errors.
6. Avoid introducing concurrency claims the implementation cannot guarantee. A read-compute-write ID generator is not an atomic ID reservation.
7. Test load/save, serialization, lookup, add, update, delete, malformed/missing storage, and persistence across reloads as applicable.

**Gate:** Verify repository function signatures and return semantics before service implementation. The service must not assume a repository method's Boolean result or exception behavior without checking it.

### Phase 5: Implement service operations

1. Follow [SERVICES_SKILL.MD](./SERVICES_SKILL.MD) to connect the selected model and repository.
2. For reads, fetch the record, translate a missing result into the documented service exception, and validate persisted data by constructing the appropriate model if that is the service contract.
3. For creates, separate caller-provided fields from server-generated fields. Set generated identifiers/timestamps deliberately, construct and validate the model before writing, then persist and return the documented result.
4. For updates, follow the agreed full-replacement or partial-update behavior. For partial updates, merge existing values then supplied values; apply immutable path/key fields last so the caller cannot change them.
5. For deletes, handle repository results accurately. An existence pre-check followed by deletion is not atomic; if delete returns `False`, decide whether to report not found or a concurrent-change condition.
6. Keep HTTP exceptions out of the service. Raise explicit domain/service exceptions where possible; do not catch broadly or disguise validation and persistence errors as not-found.
7. Test service success, not-found, duplicate, invalid-model, repository-failure, merge-precedence, and return-type behavior.

**Gate:** Service tests should pass against the repository contract. Do not wire routes around service behavior that is undefined or returns inconsistent shapes.

### Phase 6: Wire FastAPI routes and application

1. Follow [MAIN_SKILL.MD](./MAIN_SKILL.MD) to create/reuse one FastAPI app and register routes.
2. Use valid package imports where available. Dynamic imports are only a compatibility solution for existing module names that are not valid Python identifiers; do not rename files without considering callers.
3. For each operation, map its HTTP method/path, request schema, response schema, success status, and service call to the agreed API contract.
4. Prefer explicit Pydantic request models over bare dictionaries when the request shape is known. Do not accept server-owned fields simply because they are part of a response model.
5. Declare response models that match service results. Specify no-content responses and success status codes deliberately.
6. Catch only known service exceptions and map them to appropriate HTTP statuses. Keep request validation errors distinct from not-found, duplicate, and storage failures.
7. Ensure routes invoke services only; never duplicate repository or file operations in route handlers.
8. Test routes for request parsing/validation, response serialization, OpenAPI shapes, status codes, safe error details, and service failure mappings.

**Gate:** Confirm that method semantics match service behavior. In particular, do not expose partial-merge semantics through PUT without an intentional API contract; use a method/schema consistent with the intended operation.

### Phase 7: End-to-end verification

1. Run the smallest relevant checks first: model tests, repository tests, service tests, and route tests.
2. Exercise the complete flow for each supported operation: HTTP request → request validation → service → model/repository → service result/error → response model/status.
3. Confirm data survives reload/restart as applicable and does not leak between entity repositories or test cases.
4. Verify validation, not-found, conflict, and persistence failures remain distinguishable.
5. Run project formatting, lint, type checking, build, and broader tests using existing project tools when available.
6. Review the final diff for unrelated edits, stale comments, incorrect file paths, unresolved imports, duplicate definitions, and inconsistent model/repository/service/route contracts.
7. Report what changed, checks run, test outcomes, and any unresolved assumptions or limitations. Do not claim a test passed unless it was run and passed.

## Cross-Layer Contract Checklist

Before considering implementation complete, verify:

- Route request models accept exactly the intended client-provided data.
- Service-generated values cannot be overridden accidentally by the client.
- Model field names and serialization keys match repository records and response schemas.
- Repository lookups and mutations use the entity's stable unique identifier.
- Service function parameters, return types, exceptions, and repository calls match actual implementations.
- Route response models and HTTP status codes reflect service outcomes.
- No lower-level module depends on FastAPI.
- No repository I/O is duplicated in services or route handlers.
- Missing, duplicate, validation, and persistence failures are surfaced accurately.
- The implementation follows installed framework/library versions and existing project conventions.

## Common Failure Patterns

- **Starting with routes:** Request/response shapes become guesswork. Establish the model and service contracts first.
- **Using sample defaults as domain rules:** Example values are not requirements. Confirm defaults and constraints.
- **One generic model for every operation:** Create, update, and response inputs often have different required fields; model those differences explicitly when required.
- **Wrong repository key:** A relationship ID may not uniquely identify the entity. Confirm uniqueness.
- **Duplicating persistence logic:** Routes or services that write files directly bypass repository behavior and tests.
- **Overbroad `ValueError` mapping:** It can turn invalid input, corrupt persisted data, and genuine not-found into the same HTTP response.
- **Ignoring repository outcomes:** Pre-checks can race with later mutations. Inspect and handle actual update/delete results.
- **Mismatched HTTP semantics:** A partial update behind PUT can surprise clients; align method and behavior.
- **Silent storage recovery:** Returning an empty collection on parse or file errors hides data loss.
- **Unverified completion:** Static inspection alone does not validate persistence, FastAPI serialization, or the full request lifecycle.

## Completion Report

At the end of the work, summarize:

- Entity and operations implemented.
- Model, repository, service, and route files added or changed.
- API paths/methods and important contract decisions.
- Tests, builds, and checks executed with their results.
- Known limitations, unresolved questions, or intentionally deferred hardening.


## TECH STACK

Area	        Technology	Evidence / notes
Language	Python 3.14.8 in the local virtual environment	Recorded in pyvenv.cfg. The requirements file doesn’t specify a supported Python range.
API framework	FastAPI	Used in src/fast_api/main.py, which creates the app and includes routers.
Data models and validation	Pydantic	Used by model classes, including src/fast_api/model.py.
ASGI server	Uvicorn	Listed as a dependency in requirements.txt.
Data processing	pandas	Listed as a dependency in requirements.txt.
HTTP client	requests	Listed as a dependency and used in src/02_get_api_users.py.
Persistence / sample data	JSON files and in-memory Python lists	Examples include src/fast_api/data_store.py and the JSON-backed repository in day3/refactor/04_repository.py
