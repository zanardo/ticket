import os.path

from bottle import TEMPLATE_PATH, default_app

import ticket.web_admin
import ticket.web_login
import ticket.web_static
import ticket.web_ticket

TEMPLATE_PATH.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "views"))

app = default_app()
