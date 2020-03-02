SHELL ?= /bin/bash
PYTHON ?= python3
TAG=$(shell git describe --tags | sed -e 's/^v//')

.PHONY: all
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

.PHONY: data
data:
	mkdir -p data/
	test -f data/ticket.db || sqlite3 data/ticket.db < schema.sql

.PHONY: clean
clean:
	@rm -rf .venv/ build/ dist/ *.egg-info/
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete

.PHONY: run
run: .venv/pip-sync-ok
	@while :; do TICKET_CONFIG=ticket.ini .venv/bin/python -m ticket ; sleep 1 ; done

.PHONY: docker-build
docker-build:
	docker build -t zanardo/ticket:$(TAG) .

.PHONY: docker-run
docker-run: docker-build
	docker run --rm -it \
		-v /etc/localtime:/etc/localtime \
		-v ticket_dev:/app/data \
		-p 127.0.0.1:5000:5000 \
		zanardo/ticket:$(TAG)
