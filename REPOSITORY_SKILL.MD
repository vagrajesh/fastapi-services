# Repository Workflow

## Purpose

Use this guide to review or create a persistence repository for each model module in a Python project's `models` folder. A repository owns data loading, saving, serialization, and record-level CRUD. It should use the model's actual contract and the project's existing persistence choice; the examples below describe a JSON-file repository like `day3/refactor/04_repository.py`, not a requirement to use JSON in every project.

## When to Use

- A model needs a persistence adapter for JSON-backed CRUD.
- The project has several model modules and needs a clear model-to-repository mapping.
- Reviewing repository functions, serialization behavior, identifiers, or file-path handling.

## Workflow

1. Find every model module under the project's `models` directory. Read the module and identify each model class, its fields, required/defaulted values, serialization methods, and its intended API role.
2. Check for an existing repository for each model before creating one. Reuse and adapt existing behavior; do not create duplicate repositories or silently change public function names.
3. Create an explicit mapping from model module to repository module and storage file. Give each independently persisted model its own data file unless the existing contract explicitly defines a shared document or aggregate.
4. Identify the correct stable record key from the model and API contract. Do not assume every model has `invoice_id`, or that a foreign key such as `payment.invoice_id` uniquely identifies a payment. Ask for the key contract if it is not clear.
5. Keep repository responsibilities limited to persistence and serialization. Put business validation, HTTP status handling, and user-facing not-found behavior in the model, service, or API layer that owns those concerns.
6. Match the installed Pydantic version: prefer `model_dump()` when available and use the project's established v1-compatible fallback where required. Do not add a broad exception handler or silently return an empty collection when the file is missing or malformed.
7. Define and document the storage path, top-level JSON shape, missing-file policy, encoding, and write behavior. Ensure parent directories exist when the repository is responsible for creating them.
8. For each repository, implement only the operations required by its model/API contract: load, save, lookup, create/add, update, delete, and identifier generation where applicable.
9. Test each operation against that model's own storage file with representative records, missing identifiers, malformed or nonmatching identifiers, serialization inputs, and persistence across reloads.
10. Review all generated repository code and keep comments accurate. Add explanatory comments where behavior is not clear; comments do not substitute for validation or error handling.

## Model-to-Repository Mapping

Create a table before implementation and fill it from the actual project:

| Model module | Model class(es) | Repository module | Storage file | Record key |
|---|---|---|---|---|
| `models/invoiceModel.py` | `InvoiceBase`, `InvoiceCreate`, `InvoiceList`, `InvoiceUpdate`, `InvoiceDelete` | `invoice_repository.py` (example) | `data/invoice.json` (example) | `invoice_id` (confirm contract) |
| `models/paymentModel.py` | `PaymentBase`, `PaymentCreate`, `PaymentList`, `PaymentUpdate`, `PaymentDelete` | `payment_repository.py` (example) | `data/payment.json` (example) | Must be confirmed; `invoice_id` may refer to an invoice rather than uniquely identify a payment |

These names illustrate a one-model-family-to-one-repository convention; they are not claims that the example repositories or data files already exist. In the current project, `day3/refactor/04_repository.py` is invoice-specific, and the `models` folder has invoice and payment model modules. A payment repository should not be implemented with invoice CRUD or keyed by invoice ID until the payment identity and relationship contract are confirmed.

## JSON Repository Example

This compact example shows the core pattern for one model family. Replace the model name, identifier field, path, and identifier format with the confirmed project contract. Every nonblank code line has an explanatory comment.

```python
import json  # Parses and writes JSON documents.
from pathlib import Path  # Builds a path anchored to this repository module.

DATA_FILE = Path(__file__).resolve().parent / "data" / "invoice.json"  # Selects this repository's JSON file independently of the caller's working directory.

def _to_dict(invoice):  # Converts supported model inputs into JSON-ready record dictionaries.
    if isinstance(invoice, dict):  # Preserves an already serialized record.
        return invoice  # Returns the dictionary without copying or validating it.
    if hasattr(invoice, "model_dump"):  # Detects the Pydantic v2 serialization API.
        return invoice.model_dump()  # Serializes the model using its v2 method.
    return invoice.dict()  # Uses the project's Pydantic v1-compatible serialization method.

def load_invoices():  # Loads the persisted invoice collection.
    with DATA_FILE.open("r", encoding="utf-8") as file:  # Opens the configured file as UTF-8 text.
        return json.load(file)  # Parses and returns the JSON document.

def save_invoices(invoices):  # Persists the complete invoice collection.
    with DATA_FILE.open("w", encoding="utf-8") as file:  # Opens the configured file for replacement.
        json.dump(invoices, file, indent=4)  # Writes readable JSON for the complete collection.

def get_invoice_by_id(invoice_id):  # Looks up the first invoice matching the supplied key.
    for invoice in load_invoices():  # Reads records and examines them in stored order.
        if invoice.get("invoice_id") == invoice_id:  # Compares the configured key without assuming a missing key exists.
            return invoice  # Returns the first matching record.
    return None  # Signals that no matching record was found.
```

## Review of `day3/refactor/04_repository.py`

The notes below account for every executable statement and meaningful comment in the source. The source is invoice-specific; adapt its behavior deliberately rather than copying its names for unrelated models.

### Module comments and imports

- The first `#//` comment says the module loads invoices from JSON. It is documentation only; Python ignores it at runtime.
- The second `# //` comment says the data file is configured by `DATA_FILE`. It is also documentation, and its spacing differs from the first comment without changing behavior.
- `import json` imports JSON parsing and serialization functions used by the load/save methods.
- `from pathlib import Path` imports `Path` to construct a filesystem path. It is used by `DATA_FILE`.

### Path constant

- `DATA_FILE = Path(__file__).resolve().parent / "data" / "invoice.json"` resolves this source file's absolute path, selects its containing directory, and appends `data/invoice.json`. The path is independent of the process's current working directory. The expression does not create the `data` directory or JSON file.

### `_to_dict(invoice)`

- `def _to_dict(invoice):` defines a private helper by naming convention. The source does not declare parameter or return types.
- `if isinstance(invoice, dict):` checks whether the input is already a dictionary.
- `return invoice` returns that same dictionary unchanged; it is not copied or validated.
- `if hasattr(invoice, "model_dump"):` detects an attribute named `model_dump`, commonly provided by Pydantic v2.
- `return invoice.model_dump()` calls the detected method and returns its serialized value. The check only tests that the attribute exists, not that it is callable.
- `return invoice.dict()` is the fallback, commonly used by Pydantic v1. Any other object must provide a callable `dict()` method or this line raises an error.
- This conversion helper is used by `add_invoice` and `update_invoice`; `append_invoice` intentionally does not use it.

### `load_invoices()`

- The preceding comment describes loading invoices; comments have no runtime effect.
- `def load_invoices():` declares the loader without arguments.
- `with open(DATA_FILE, "r") as f:` opens the configured file in text read mode and closes it when the block exits. The source relies on the platform's default text encoding.
- `return json.load(f)` parses the full JSON document and returns its Python value. The function assumes the file exists, contains valid JSON, and has the collection shape expected by callers. Missing files, invalid JSON, and I/O failures propagate as exceptions.

### `save_invoices(invoices)`

- The preceding comment documents the save operation only.
- `def save_invoices(invoices):` declares the writer with the complete collection as its input.
- `with open(DATA_FILE, "w") as f:` opens the file in text write mode, truncating existing contents before writing. It also closes the file on exit; no explicit encoding is selected.
- `json.dump(invoices, f, indent=4)` serializes the supplied value as indented JSON. It replaces the entire document; it does not append a JSON record.
- The function does not create parent directories, use a temporary file/atomic replace, lock concurrent writers, or validate the collection shape.

### `get_invoice_by_id(invoice_id)`

- The preceding comment documents the lookup and says a miss returns `None`.
- `def get_invoice_by_id(invoice_id):` declares lookup by an argument named `invoice_id`.
- `for invoice in load_invoices():` reads the full file and iterates records in their stored order. If loading fails or returns a non-iterable shape, that failure propagates.
- `if invoice.get("invoice_id") == invoice_id:` compares the record's `invoice_id` value to the requested ID. This expects each record to support `.get()`.
- `return invoice` returns the first matching record as-is; later duplicate IDs are not considered.
- `return None` is reached only if no record matches.

### `get_next_invoice_id()`

- `def get_next_invoice_id():` declares a generator for the invoice-specific sequential ID format.
- `sequence_numbers = [` starts a list comprehension of accepted numeric suffixes.
- `int(invoice_id[3:])` converts the text after the first three characters to an integer.
- `for invoice in load_invoices()` reads all records and visits each one.
- `if isinstance(invoice_id := invoice.get("invoice_id"), str)` uses an assignment expression to fetch the ID once and requires it to be a string.
- `and invoice_id.startswith("INV")` restricts IDs to the uppercase `INV` prefix.
- `and invoice_id[3:].isdigit()` accepts only a nonempty all-digit suffix; malformed values and other prefixes are ignored.
- `]` completes the comprehension. It does not check for duplicates, sequence gaps, case variants, or concurrency.
- `return f"INV{max(sequence_numbers, default=0) + 1:03d}"` increments the largest accepted suffix (using zero when there are none), then pads to at least three digits. It does not truncate larger values, so 999 is followed by 1000.
- This is a read-then-compute helper, not a reservation. Concurrent callers may receive the same next ID unless the surrounding persistence design prevents it.

### `add_invoice(invoice)`

- The inline comment on the function declaration describes its purpose only.
- `def add_invoice(invoice):` declares the create helper.
- `invoices = load_invoices()` reads the whole existing collection.
- `invoices.append(_to_dict(invoice))` serializes model-like inputs (or leaves dictionaries unchanged) and adds the result at the end of the collection.
- `save_invoices(invoices)` rewrites the full collection. The function does not generate an ID, reject duplicates, validate the record, or return an explicit result.

### `append_invoice(invoice)`

- The inline comment on the declaration describes an append operation.
- `def append_invoice(invoice):` declares a second helper with a different input behavior from `add_invoice`.
- `invoices = load_invoices()` reads the entire current collection.
- `invoices.append(invoice)` appends the argument unchanged. Unlike `add_invoice`, this does not convert a Pydantic model to a dictionary; a model instance may therefore fail JSON serialization during saving.
- `save_invoices(invoices)` rewrites the full collection after the append.
- Preserve both functions only if both names/behaviors are part of the required API. Otherwise choose one documented create operation and make its serialization contract explicit.

### `update_invoice(invoice_id, updated_invoice)`

- The inline comment on the declaration says this updates an invoice and saves it.
- `def update_invoice(invoice_id, updated_invoice):` accepts the identifier to find and replacement record.
- `invoices = load_invoices()` loads the entire collection.
- `for index, invoice in enumerate(invoices):` iterates in order while tracking each record's position.
- `if invoice.get("invoice_id") == invoice_id:` selects the first matching record.
- `invoices[index] = _to_dict(updated_invoice)` replaces the whole record, not selected fields, and normalizes the new value using `_to_dict`. The replacement's own `invoice_id` is not forced to match the lookup ID.
- `save_invoices(invoices)` rewrites the entire file immediately after the first match.
- `return True` reports that a matching record was replaced and saved.
- `return False` reports a miss. Because it occurs after the loop, the file is not saved on a miss.
- The function does not implement partial update semantics, enforce key immutability, validate fields, or report a service/API-level error.

### `delete_invoice(invoice_id)`

- The inline comment on the declaration describes removal and persistence.
- `def delete_invoice(invoice_id):` accepts the invoice identifier.
- `invoices = load_invoices()` loads the complete collection.
- `for index, invoice in enumerate(invoices):` scans records in stored order with their positions.
- `if invoice.get("invoice_id") == invoice_id:` selects the first matching record.
- `del invoices[index]` removes that record from the in-memory list; later duplicates remain.
- `save_invoices(invoices)` rewrites the full collection after removal.
- `return True` reports successful deletion.
- `return False` reports that no record matched and does not write the file.
- The function returns a Boolean rather than raising a not-found error; callers above this layer decide how a miss is presented.

## Per-Model Repository Design

- Make the mapping explicit for every model module discovered. For example, `models/invoiceModel.py` can map to `invoice_repository.py` and `data/invoice.json`; `models/paymentModel.py` can map to `payment_repository.py` and `data/payment.json`.
- Model variants such as `InvoiceCreate`, `InvoiceList`, `InvoiceUpdate`, and `InvoiceDelete` may describe different API operations but can share one repository and one persistence file when they represent the same stored entity.
- A separate model file does not automatically require a separate physical data file if the domain defines an aggregate or shared storage format. Follow the contract and document the reason for shared storage.
- Each repository should use its own model's record key and serializer. Never hardcode `invoice_id` in a generic helper used for payments or other entities.
- In the inspected payment model, `PaymentBase` has `invoice_id` and optional `paid`; the file does not demonstrate a unique payment ID. Determine whether there can be multiple payments per invoice and what identifies one payment before implementing payment lookup/update/delete.
- Keep model definitions in `models`, repository functions in repository modules, orchestration/business rules in services, and HTTP response mapping in API routes.
- Avoid circular imports. If the repository only serializes an input model by its supported methods, it may not need to import all model classes; if runtime validation is required, define the dependency direction deliberately.

## Reliability and Compatibility Rules

- Use a stable key and define duplicate behavior. The source returns, updates, and deletes only the first duplicate, while next-ID generation only scans matching formats; retain that behavior only when intended.
- Make the JSON shape explicit, usually an array of object records for a simple collection. Validate loaded data at a suitable boundary instead of assuming malformed structures are safe.
- Choose missing-file behavior deliberately: initialization, explicit error, or another project-standard policy. Do not silently disguise file corruption as an empty collection.
- Use explicit UTF-8 encoding and create the parent directory if repository initialization owns that responsibility.
- For write reliability or concurrent access requirements, use an established project mechanism such as atomic replacement or a database. The source's direct whole-file write is simple but can lose updates or leave incomplete data after interruption.
- Preserve JSON-serializable values. Pydantic serialization does not guarantee every custom value is JSON-compatible unless the model and serialization options account for it.
- Keep exception handling narrow and visible. Do not catch all errors and return `[]`, `None`, or `False` as if persistence succeeded.
- Document intentional behavior changes when improving the source, such as validation, atomic writes, encoding, duplicate handling, or different failure policies.

## Completion Checks

- Every model module under `models` has been reviewed and has an intentional repository/storage mapping, or an explicit reason it needs no independent repository.
- Repository filenames, data filenames, collection shapes, keys, and public operations match the project contract.
- Each repository loads and saves only the intended model's records.
- Serialization is tested for dictionaries and the Pydantic version(s) used by the project.
- Lookup, ID generation, add, update, and delete behavior—including duplicate and not-found cases—is tested.
- Missing files, malformed JSON, invalid record shapes, and write errors remain observable and are handled only according to an explicit policy.
- Repeated load/save operations preserve data, and comments accurately describe behavior.
