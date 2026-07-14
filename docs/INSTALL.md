# Install

The package, optional API support, and development extras are defined by
`pyproject.toml`. Use the bounded operator route in the root `AGENTS.md`;
exact CLI syntax belongs to the installed entry point and parser, while
repository validation belongs to `scripts/validate_connector.py` and the CI
workflow.

The connector falls back to ignored `.connector-state/` roots for tiny fixture
runs. For real data, configure external storage roots from `.env.example`.
