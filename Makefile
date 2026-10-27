.PHONY: install install-eval check demo test lint

install:
	python -m pip install -e '.[dev]'

install-eval:
	python -m pip install -e '.[eval,dev]'

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --junitxml=test-results.xml

check: lint test

demo:
	rag-gate demo
