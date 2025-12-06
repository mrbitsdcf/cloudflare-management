# Roadmap

- [X] Logging to file: add optional log file output (rotating or size-based), simplify console logs, and expose a `--log-file` flag with sensible defaults.
- [ ] Removal flag: support `--force` in `remove-dns-record` to skip interactive confirmation while keeping confirmation as default.
- [ ] Module split: refactor `cfmanager.py` into dedicated modules (e.g., `lib/clients.py`, `commands/create.py`, `commands/remove.py`, `commands/list.py`) while preserving current CLI behavior.
- [ ] Packaging: add packaging metadata (pyproject.toml/setup.cfg), entry point for `cloudflare-manager` CLI, and publishable wheel/sdist so installation via `pip install cloudflare-manager` works.
- [X] Testing: introduce basic unit tests for token handling, listing, create/remove flows (mocking HTTP), and CLI entry points.
