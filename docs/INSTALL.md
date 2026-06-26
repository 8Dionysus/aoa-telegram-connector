# Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python scripts/validate_connector.py
PYTHONPATH=src python -m aoa_telegram_connector.cli doctor
```

The connector falls back to ignored `.connector-state/` roots for tiny fixture
runs. For real data, configure external storage roots from `.env.example`.
