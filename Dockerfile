FROM debian:buster

RUN set -x ; \
	export DEBIAN_FRONTEND=noninteractive && \
	apt-get update && \
	apt-get install -y \
		python3 \
		python3-venv \
		python3-dev \
		sqlite3 \
		&& \
	rm -rf /var/lib/apt/lists/*

COPY ticket /app/ticket
COPY static /app/static
COPY views /app/views
COPY requirements.txt /app/requirements.txt
COPY ticket.ini /app/ticket.ini
COPY schema.sql /app/schema.sql

WORKDIR /app
VOLUME /app/data

RUN set -x ; \
	python3.7 -m venv .venv && \
	.venv/bin/python -m pip install -U pip setuptools wheel && \
	.venv/bin/python -m pip install gunicorn && \
	.venv/bin/python -m pip install -r requirements.txt

ENV DUID="11592" \
	DGID="11592" \
	GUNICORN_WORKERS="2" \
	GUNICORN_BIND="0.0.0.0:5000"

CMD if [ ! -f /app/data/ticket.db ]; then \
		sqlite3 /app/data/ticket.db < /app/schema.sql ; \
	fi && \
	chown -R "$DUID:$DGID" /app/data && \
	exec setpriv --reuid="$DUID" --regid="$DUID" --clear-groups \
	.venv/bin/gunicorn \
		--timeout 30 \
		--workers "$GUNICORN_WORKERS" \
		--bind "$GUNICORN_BIND" \
		--error-logfile - \
		--access-logfile - \
		--access-logformat '%(t)s | %(p)s | %(h)s | %({X-Real-IP}i)s | %(L)s | %(s)s | %(r)s' \
		--env TICKET_CONFIG=/app/ticket.ini \
		ticket.app:app
