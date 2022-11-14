VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip


$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

install:
	make $(VENV)/bin/activate

clean:
	rm -rf __pycache__

fmt:
	black ./

lint:
	pylint src/

types:
	mypy src/ --strict

check:
	make install
	make fmt
	make lint
	make types

test-unit:
	python -m pytest tests/unit

test-e2e:
	python -m pytest tests/e2e

db:
	# TODO - Should only build if necessary.
	docker build -t test_db -f Dockerfile.db .;
	# We try to run the container, but if its already running it will result in
	# docker: Error response from daemon: Conflict. The container name "/testDB" is already in use by container
	# So we supress this error with ; exit 0 and continue.
	docker run -d -p 5432:5432 test_db; exit 0;
	# sleep just long enough for the machine to recognize the establishing container.
	sleep 1s

test-db:
	if !(docker ps | grep test_db >/dev/null); then make db; fi
	python -m pytest tests/db
	python -m pytest tests/queries

test-all:
	make test-unit
	make test-e2e
	make test-db
