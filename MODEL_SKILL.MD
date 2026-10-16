---
name: model-workflow
description: 'Define or review Pydantic data models in Python projects. Use when creating model classes, fields, defaults, validation rules, or request and response schemas.'
argument-hint: 'Describe the model to define or review, including its fields and behavior.'
---

# Model Workflow

## Purpose

Define clear, validated Python data models that fit the project's existing contracts and Pydantic version. Use the transaction examples below as illustrations; replace their names, fields, and values with those required by the project.

## Workflow

1. Read the relevant model, API contract, and dependency files before changing code. Identify the Pydantic major version and the project's naming, import, and validation conventions.
   If Pydantic is not installed or its version cannot be determined from the project's dependency files, tell the user, ask which major version to target, and do not write the model until confirmed.
2. Check whether an equivalent model already exists. Reuse or adapt it rather than creating competing definitions. If its existing fields or behavior conflict with the requested contract, explain the differences and get confirmation before changing them.
3. Translate the required data contract into fields with explicit types. Preserve required versus optional fields, defaults, aliases, constraints, and extra-field behavior only as specified by the contract.
4. Use Pydantic APIs compatible with the installed major version. Do not copy version-specific configuration or serialization methods without checking the project's version.
5. Use `default_factory` for values that must be computed separately for each instance, such as a creation timestamp. Do not evaluate a changing value like `datetime.now()` while the model class is being defined.
6. Add a concise explanatory comment to every nonblank line of model code, including imports, class declarations, fields, decorators, and statements. Put comments inline when valid Python syntax permits. Comments must explain purpose, not merely repeat the code. Do not add comments to blank lines.
7. Keep field names idiomatic for the project (normally `snake_case` in Python). Do not change an existing external field name or wire-format alias without checking compatibility.
8. Validate the model with representative valid data, omitted required fields, invalid values, defaults, and serialization behavior appropriate to the contract.

## Transaction Example

The following is an illustrative base model and create model. Each nonblank code line has a comment explaining its role. Adapt field names, types, and example values to the target project's contract.

```python
import datetime  # Provides the date and time types used by the model.
import pydantic  # Provides BaseModel and Field for validated model declarations.

class TransactionBase(pydantic.BaseModel):  # Defines fields shared by transaction representations.
    transaction_id: str  # Stores the transaction identifier as text.
    billed_amount: float = 0.0  # Uses zero as the example amount when the contract permits a default.
    card_last_four: str = "0000"  # Uses a placeholder string only if the contract defines this default.
    transaction_date: datetime.datetime  # Stores when the transaction occurred.
    card_provider: str = "Uncategorized"  # Uses the example provider label as a default.
    vendor: str = "None"  # Stores the literal text "None"; use an optional type and None only if null is intended.

class TransactionCreate(TransactionBase):  # Adds fields specific to creating a transaction.
    created_at: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)  # Computes a fresh timestamp for each instance; use the contract's required timezone policy.
```

## Line-by-Line Review of the Supplied Example

- The opening comment describes the purpose of the file. Keep a short purpose comment when it helps future maintainers.
- The commented `import pydantics` line is not executable, and `pydantics` is misspelled. The executable import is `import pydantic`; avoid preserving a misleading commented-out import.
- `import datetime` makes the standard-library datetime module available. The field annotation `datetime.datetime` refers to its datetime class.
- The comment above `TransactionBase` describes its role. Keep the class name aligned with the project's domain terminology.
- `class TransactionBase(pydantic.BaseModel):` creates a Pydantic model base class.
- `transaction_id: str` is required because it has no default.
- `billed_amount: float = 0.0` is not required at construction because it has a default. Confirm that zero is a valid domain default rather than assuming it.
- `card_last_four: str = "0000"` is also optional at construction. Confirm whether a placeholder is valid data; do not mistake it for a real card value.
- `transaction_date: datetime.datetime` is required because it has no default. Confirm whether the API contract expects a timezone-aware datetime.
- `card_provider: str = "Uncategorized"` uses a string default. Use an enum or constrained type only when the contract requires one.
- `vendor: str = "None"` stores the literal string `"None"`, not Python's `None` value. If the field is nullable, define and validate its optionality according to the project's Pydantic version and contract.
- The comment before `TransactionCreate` labels the model's intended operation. It is documentation, not behavior; verify its fields against the actual create request contract.
- `class TransactionCreate(TransactionBase):` inherits all base fields, including required `transaction_id` and `transaction_date`. Check whether a create request should require those values or whether the API assigns them.
- `pass` has no runtime effect and can be omitted when the class has other members. It does not prevent later class-body declarations.
- `created_at: datetime.datetime = datetime.datetime.now()` evaluates `now()` once when the class is defined, so instances can share a stale timestamp. Use `pydantic.Field(default_factory=...)` to compute a value per instance; follow the domain's timezone policy.
- The comment before `TransactionList` is descriptive only. Confirm whether list responses need a distinct model or can reuse the base/response model.
- `class TransactionList(TransactionBase):` inherits every base field and its defaults; it does not add list behavior by itself.
- Its `pass` statement adds no fields or behavior. A collection of these models is normally represented by the API response type, not by an empty subclass unless the project has a reason for it.
- The comment before `TransactionUpdate` is descriptive only. Confirm whether updates are full replacements or partial updates.
- `class TransactionUpdate(TransactionBase):` inherits required fields from the base, which may be inappropriate for a partial update. Model partial updates explicitly only when the API contract requires optional fields.
- `Updated_date` has an uppercase initial and does not follow typical Python `snake_case` conventions. Prefer `updated_date` for a new internal field; preserve an external name with a Pydantic alias only when the wire contract requires it.
- `Updated_date` also calls `datetime.datetime.now()` at class definition time. Use a per-instance factory when a generated timestamp is intended, and do not add a generated update timestamp unless the contract assigns responsibility for it.
- The comment before `TransactionDelete` is descriptive only. Check whether the API actually needs a deletion request/response model.
- `class TransactionDelete(TransactionBase):` inherits every base field, even though deletion may require only an identifier. Do not infer a delete payload shape from the class name; follow the API contract.
- Its `pass` statement adds no fields or behavior and is unnecessary if an empty subclass is not required.

## Modeling Rules

- Do not infer business rules from example values. Defaults such as `0.0`, `"0000"`, and `"Uncategorized"` are examples, not universal requirements.
- Distinguish a required field, an optional field, and a field with a default. They have different validation and serialization behavior.
- Do not add constraints such as positive amounts, enumerated provider names, or date ordering without an explicit requirement. List proposed rules in your reply under **Pending validation requirements** and wait for confirmation before applying them.
- If multiple models share fields, use inheritance only when the shared validation and requiredness genuinely match. Avoid empty create, list, update, or delete subclasses that imply behavior they do not implement.
- Keep comments useful and truthful. Update them when code behavior changes, and do not claim that a field is unique, sensitive, or validated unless the implementation enforces that property.
- Treat sensitive payment data carefully. A field name or comment does not make storage or logging of payment data safe; include only data required by the contract.

## Completion Checks

- Model imports succeed in the project's selected environment.
- A valid representative instance can be created and serialized using the project's Pydantic version.
- Required fields fail validation when omitted, while defaulted and optional fields behave as specified.
- Invalid values produce the expected validation errors; values coercible under the configured validation mode are handled according to the contract.
- Dynamic defaults are computed per instance, and datetime timezone behavior matches the project contract.
- API and service layers use the intended shared model definitions without duplicate or conflicting schemas.
- Every nonblank line of newly written model code has an accurate explanatory comment, as required by this workflow.
