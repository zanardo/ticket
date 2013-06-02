# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

import re
import os
import sys
import zlib
import time
import bottle
import getopt
import random
import getopt
import os.path
import sqlite3
import datetime
import mimetypes

from uuid import uuid4
from hashlib import sha1
from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

import config

import ticket.db
import ticket.user
import ticket.webadmin
import ticket.weblogin
import ticket.webticket

VERSION = '1.6dev'

###############################################################################
# Roteamento de URIs
###############################################################################

@route('/static/:filename')
def static(filename):
    # Retorna um arquivo estático em ./static
    assert re.match(r'^[\w\d\-]+\.[\w\d\-]+$', filename)
    return static_file('static/%s' % filename, root='.')


@get('/change-password')
@ticket.user.requires_auth
@view('change-password')
def changepassword():
    # Tela de alteração de senha do usuário
    username = ticket.user.currentuser()
    return dict(username=username, version=VERSION,
        userisadmin=ticket.user.userisadmin(username))


@post('/change-password')
@ticket.user.requires_auth
def changepasswordsave():
    # Altera a senha do usuário
    assert 'oldpasswd' in request.forms
    assert 'newpasswd' in request.forms
    assert 'newpasswd2' in request.forms
    oldpasswd = request.forms.oldpasswd
    newpasswd = request.forms.newpasswd
    newpasswd2 = request.forms.newpasswd2
    username = ticket.user.currentuser()
    if not ticket.user.validateuserdb(username, oldpasswd):
        return 'senha atual inválida!'
    if newpasswd.strip() == '' or newpasswd2.strip() == '':
        return 'nova senha inválida!'
    if newpasswd != newpasswd2:
        return 'confirmação de nova senha diferente de nova senha!'
    passwdsha1 = sha1(newpasswd).hexdigest()
    with ticket.db.db_trans() as c:
        c.execute("update users set password = :passwdsha1 "
            "where username = :username", locals())
    return redirect('/')
