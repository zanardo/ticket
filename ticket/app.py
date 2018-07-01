# -*- coding: utf-8 -*-

import os.path

from bottle import default_app, TEMPLATE_PATH

import ticket.webadmin
import ticket.weblogin
import ticket.webticket
import ticket.webstatic

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
