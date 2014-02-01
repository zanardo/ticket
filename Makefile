all: venv

venv: .venv/bin/activate

.venv/bin/activate: requirements.txt
	test -d .venv || virtualenv-2.7 --no-site-packages --distribute .venv
	. .venv/bin/activate; pip install -r requirements.txt
	touch .venv/bin/activate

run-server-devel: venv
	while :; do ./.venv/bin/python server.py --host 127.0.0.1 --port 5000 --debug ; sleep 0.5 ; done

run-server: venv
	./.venv/bin/python server.py --host 0.0.0.0 --port 5000
