# Contributing

Install `.[eval,dev]`, run `make check`, and run `make demo` before opening a PR.

Useful contributions include expert-reviewed evaluation cases, new retrieval or generator adapters, judge calibration experiments, and reproducible failure reports.

Keep references and gold labels outside application generation. Preserve metric namespaces and explicit error states. Add contract tests for new SDK integrations. Never turn a failed or missing evaluation into a numeric passing score.

Synthetic dataset changes should be made in `scripts/build_dataset.py` and regenerated with `python scripts/build_dataset.py`. Commit both the script and JSONL outputs. For real cases, document data permissions and remove proprietary information before contributing.

For dependency changes, update `pyproject.toml`, run `uv lock`, regenerate the two requirements exports using the commands in `docs/ARCHITECTURE.md`, and run the full SDK suite in a clean environment. Do not upgrade LangChain pins without proving RAGAS still imports and evaluates.
