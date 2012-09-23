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

from bottle import route, request, run, view, response, static_file, \
    redirect, local

def connectdb(dbpath):
    db = getattr(local, 'db', None)
    if db is None:
        local.db = sqlite3.connect(dbpath)
    return local.db

@route('/new-ticket')
@view('new-ticket')
def newticket():
    return dict()

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
