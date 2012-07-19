#!/usr/bin/env python
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#

import os
import sys
import getopt
import sqlite3
import bottle

from bottle import route, request, run, view, response, static_file, \
    redirect, local


def connectdb(dbpath):
    db = getattr(local, 'db', None)
    if db is None:
        local.db = sqlite3.connect(dbpath)
    return local.db


if __name__ == '__main__':

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:p:d:')
    except getopt.GetoptError, err:
        usage()

    address = '0.0.0.0'
    port = 8080
    dbpath = 'ticket.db'

    for o, a in opts:
        if o == '-a': address = a
        elif o == '-p': port = a
        elif o == '-d': dbpath = a
        else: usage()

    debug = True

    bottle.debug(debug)
    os.chdir(os.path.dirname(__file__))
    try:
        run(host=address, port=port, server='auto', reloader=debug)
    except KeyboardInterrupt:
        exit(0)
