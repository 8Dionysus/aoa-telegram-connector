# Starter Proof

The starter proof is no-network and synthetic.

It demonstrates:

- Bot API mode sees public/channel-visible messages.
- TDLib user-session mode sees the connected-account private DM fixture.
- The graph preserves reply, edit, pin, warning, and supersession context.
- Answer packets distinguish `answered`, `insufficient_permission`, and
  `insufficient_evidence`.

Run:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize fixture --mode tdlib_user_session
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph
PYTHONPATH=src python -m aoa_telegram_connector.cli eval permissions
PYTHONPATH=src python -m aoa_telegram_connector.cli eval answer-packets
```
