VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip


$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt


clean:
	rm -rf __pycache__

fmt:
	black ./

lint:
	pylint src/

types:
	mypy src/ --strict

check:
	make fmt
	make lint
	make types

test-unit:
	python -m pytest tests/unit

test-e2e:
	python -m pytest tests/e2e

test-db:
	python -m pytest tests/db
	python -m pytest tests/queries

test-all:
	make test-unit
	make test-e2e
	make test-db
