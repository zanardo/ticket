SHELL ?= /bin/bash
PYTHON ?= python3

all: .venv/pip-sync-ok

requirements.txt: requirements.in
	.venv/bin/pip-compile

.venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install pip-tools

.venv/pip-sync-ok: .venv requirements.txt
	.venv/bin/pip-sync
	@touch .venv/pip-sync-ok

data:
	mkdir -p data/
	test -f data/ticket.db || sqlite3 data/ticket.db < schema.sql

clean:
	@rm -rf .venv/ build/ dist/ *.egg-info/
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete

test: .venv/pip-sync-ok
	.venv/bin/python tests.py

run: .venv/pip-sync-ok
	@while :; do TICKET_CONFIG=ticket.ini .venv/bin/python -m ticket ; sleep 1 ; done

.PHONY: all data clean test run
