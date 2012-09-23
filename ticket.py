#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#

import re
import os
import sys
import getopt
import bottle
import psycopg2

from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

db = psycopg2.connect(database='ticket', user='postgres')
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

@get('/new-ticket')
@view('new-ticket')
def newticket():
    return dict()

@post('/new-ticket')
def newticketpost():
    title = request.forms.get('title')
    c = db.cursor()
    c.execute('''
        INSERT INTO TICKETS (
            title, "user"
        )
        VALUES ( %s, %s )
        RETURNING id
    ''', (title, '') )
    ticket_id = c.fetchone()[0]
    db.commit()
    return redirect('/%s' % ticket_id)

@route('/static/:filename')
def static(filename):
    if not re.match(r'^[\w\d]+\.[\w\d]+$', filename):
        return 'invalid filename'
    return static_file('static/%s' % filename, root='.')

if __name__ == '__main__':

    address = '0.0.0.0'
    port = 8080
    dbpath = 'ticket.db'

    bottle.debug(True)
    run(host=address, port=port, server='auto', reloader=True)
