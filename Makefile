PYTHON ?= python
PIP ?= $(PYTHON) -m pip
RUFF ?= $(PYTHON) -m ruff
PYTEST ?= $(PYTHON) -m pytest

.PHONY: install-dev lint format test ci

install-dev:
	$(PIP) install -U pip
	$(PIP) install -e '.[dev,pdf]'

lint:
	$(RUFF) format --check .
	$(RUFF) check .

format:
	$(RUFF) format .

test:
	$(PYTEST) -q

ci: lint test
