# Research: CloudOps Deployment Management & Readiness Tracker

## Decisions

### Standard-library CLI and test stack

- **Decision**: Use `argparse` for the `deploy` command group and its `create`, `list`, `view`, `update`, `status`, and `readiness` subcommands. Use `unittest` for automated tests.
- **Rationale**: Both are included with Python, support a maintainable modular application, and avoid unnecessary third-party dependencies for a local CLI.
- **Alternatives considered**: A third-party CLI framework could provide richer formatting but is not needed for the specified interface. A third-party test runner is likewise unnecessary for the initial scope.

### Domain model and deterministic rules

- **Decision**: Represent domain records with dataclasses and fixed status/check values with enums. Keep lifecycle transitions in one explicit transition table and readiness evaluation in deterministic, side-effect-free rules. Re-evaluate the gates when a guarded status change is requested.
- **Rationale**: A single domain implementation prevents CLI paths from independently changing state or bypassing mandatory checks. Dataclass annotations help organize records; explicit validation is still required when loading persisted input.
- **Alternatives considered**: Updating status directly from individual commands increases the risk of inconsistent state. A workflow engine or validation framework would add complexity without a need in this local single-project application.

### JSON state storage and corruption behavior

- **Decision**: Store records, readiness results, human decisions, audit events, and a schema version together in one JSON document. On a missing file, start with an empty state. On malformed JSON, invalid stored records, or an unsupported schema version, report an actionable error and preserve the original file without overwriting it.
- **Rationale**: A single snapshot keeps deployment state and its audit event in the same commit boundary. Parseable JSON still requires schema and enum validation. Refusing to silently reset protects existing evidence.
- **Alternatives considered**: Multiple files create multi-write consistency problems. JSON Lines can suit large append-only logs but add coordination and recovery concerns unjustified for the expected local scale. Automatic repair could discard information, so recovery remains explicit.

### Safe persistence updates

- **Decision**: Write the complete new JSON snapshot to a temporary file in the destination directory, flush and sync it, then replace the target with `os.replace`. Clean up the temporary file if the operation fails. Do not promise protection from simultaneous writers.
- **Rationale**: Same-directory replacement prevents readers from observing a partially written destination and avoids a cross-filesystem rename. Atomic visibility is not the same as a multi-process transaction or a guarantee against lost updates.
- **Alternatives considered**: Directly truncating and rewriting the destination risks a partial file if interrupted. Locking or conflict detection can be added if concurrent writers become an explicit requirement.

### Audit and human decision recording

- **Decision**: Record human ACCEPT/REJECT decisions as distinct audit events with actor, timestamp, and reason. Persist the decision and its audit event together with the deployment state. Keep audit history append-only through application operations.
- **Rationale**: Approval must be independent of APPROVED status, and a coherent snapshot avoids a decision being stored without its corresponding audit evidence.
- **Alternatives considered**: Separate audit and state files can diverge on partial failure. A local application-managed audit trail is not tamper-proof; stronger tamper evidence is outside the stated local-only scope.

### Deterministic identifiers and timestamps

- **Decision**: Keep ID and timestamp generation behind injectable functions in domain/service boundaries.
- **Rationale**: Tests can assert stable values without changing production behavior, and persisted audit timestamps remain attributable to individual actions.
- **Alternatives considered**: Reading the system clock or generating IDs throughout CLI commands makes behavior less consistent and harder to test.

## Sources

- Python documentation: [`argparse`](https://docs.python.org/3/library/argparse.html), [`dataclasses`](https://docs.python.org/3/library/dataclasses.html), [`enum`](https://docs.python.org/3/library/enum.html), [`json`](https://docs.python.org/3/library/json.html), [`os.replace`](https://docs.python.org/3/library/os.html#os.replace), [`tempfile`](https://docs.python.org/3/library/tempfile.html), [`unittest`](https://docs.python.org/3/library/unittest.html).
