# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-25

### Added

- `py.typed` marker (PEP 561), so the package ships its type information.
- Strict `mypy` configuration for the package and examples.
- `mypy` checks in CI, in the pre-commit push stage, and in `make typecheck`.
- `FIXContainer.get()` overloads: without a default it returns `str`, with a
  default it returns `str | T`.
- Ruff checks in CI and a hardened lint configuration.
- CI runs the test suite on Python 3.11 through 3.15.
- Python 3.12 through 3.15 classifiers.
- Development environment setup documented.
- Tests: `test_xml_group_required_flags`,
  `test_get_returns_default_for_missing_tag`, and
  `test_schema_validation_required_group` with the `schema_required_group.xml`
  fixture.

### Changed

- Replaced black, isort, and flake8 with ruff; reformatted the codebase.
- Switched `datetime.utcnow()` to `datetime.now(UTC)`.
- Replaced `%` formatting with f-strings and narrowed exception handling.
- `FTag` is now compatible with `str`; type hints fixed and redundant `object`
  removed.
- `FIXContainer.query()`, `FIXTester.acceptor_sent_query()`, and
  `FIXTester.initiator_sent_query()` now declare `dict[..., str | None]`, which
  matches the values they already returned for missing tags.
- Connection `port` parameters accept `int | str`; values are still coerced with
  `int(port)`.
- `dev` extras pin `mypy==2.4.1`.
- Date validation tests accept the CPython 3.14+ `strptime` error message for
  out-of-range days.

### Fixed

- `FIXSchema.validate()`, `_validate_header()`, and
  `SchemaGroup.validate_group()` now raise `FIXMessageError` when a group marked
  `required='Y'` in the schema is absent. Previously required groups were not
  enforced.
- Group members in `SchemaSet.required` store the group's `field_required` flag
  instead of its member dictionary.
- `Journaler` asserts `lastrowid` after inserting the session row.
- `Journaler` closes its cursor and connection on shutdown.
- Header components parse after components are loaded; an unresolvable header
  component reference raises `RuntimeError` at load instead of leaving
  `FIXSchema._header` as `None`.
- Type annotations across `asyncfix` and `examples`; `mypy --strict` is clean.

### Breaking

- Schema validation rejects messages that omit a required group. Such messages
  were previously accepted even though the schema declared the group mandatory.
