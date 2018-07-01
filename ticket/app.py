import os.path

from bottle import default_app, TEMPLATE_PATH

import ticket.web_admin
import ticket.web_login
import ticket.web_ticket
import ticket.web_static

TEMPLATE_PATH.insert(
    0,
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        'views'
    )
)

app = default_app()
