PYTHON=python2

all: .venv

.venv: setup.py
	@test -d .venv || virtualenv -p $(PYTHON) .venv
	@.venv/bin/pip install -e .
	@touch .venv

data:
	mkdir -p data/
	test -f data/ticket.db || sqlite3 data/ticket.db < schema.sql

clean:
	@rm -rf .venv/ build/ dist/ *.egg-info/
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete

test: .venv
	.venv/bin/python tests.py

run: .venv
	while :; do TICKET_SETTINGS=`pwd`/ticket.conf .venv/bin/python -m ticket ; sleep 1 ; done

run-gunicorn: .venv
	.venv/bin/gunicorn \
		--bind 127.0.0.1:5000 \
		--workers 2 \
		--error-logfile - \
		--name ticket \
		--pid /tmp/ticket.pid \
		--env TICKET_SETTINGS=`pwd`/ticket.conf \
		ticket.app:app

.PHONY: all data clean test run run-gunicorn
