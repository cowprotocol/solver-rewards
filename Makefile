PYTHON = python3

VENV      = venv
ACTIVATE := source $(VENV)/bin/activate

DOCKER = docker
TESTDB = solver-rewards-test-db

# Write a marker .install file to indicate that the dependencies have been
# installed.
INST := $(VENV)/.install
$(INST): requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE); pip install --upgrade pip
	$(ACTIVATE); pip install -r requirements.txt
	touch $@

.PHONY: install
install: $(INST)

.PHONY: clean
clean:
	rm -rf __pycache__ venv

.PHONY: fmt
fmt: install
	$(ACTIVATE); black ./

.PHONY: lint
lint: install
	$(ACTIVATE); pylint src/

.PHONY: types
types: install
	$(ACTIVATE); mypy src/ --strict

.PHONY: check
check: fmt lint types

.PHONY: test-unit
test-unit: install
	$(ACTIVATE); python -m pytest tests/unit

.PHONY: test-e2e
test-e2e: install
	$(ACTIVATE); python -m pytest tests/e2e

.PHONY: db
db:
	$(DOCKER) build -t $(TESTDB) -f Dockerfile.db .;

.PHONY: test-db
test-db: install db
	if ! $(DOCKER) container inspect $(TESTDB) >/dev/null 2>&1; then \
		$(DOCKER) run --rm -d -p 5432:5432 $(TESTDB) \
		`# sleep just long enough for the machine to recognize the establishing container.` \
		sleep 1s \
	fi
	$(ACTIVATE); python -m pytest tests/db
	$(ACTIVATE); python -m pytest tests/queries

.PHONY: test-integration
test-integration: install
	$(ACTIVATE); python -m pytest tests/integration

.PHONY: test-all
test-all: test-unit test-e2e test-db test-integration
