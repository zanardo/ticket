# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

from bottle import get, view, redirect, request, post, response
from hashlib import sha1

import ticket.user
import ticket.db

# Tela de login
@get('/login')
@view('login')
def login():
    # Retorna tela de login
    return dict(version=ticket.VERSION)


# Valida login
@post('/login')
def validatelogin():
    # Valida login do usuário
    assert 'user' in request.forms
    assert 'passwd' in request.forms
    user = request.forms.user
    passwd = request.forms.passwd
    if ticket.user.validateuserdb(user, passwd):
        session_id = ticket.user.makesession(user)
        response.set_cookie(ticket.user.cookie_session_name(), session_id)
        return redirect('/')
    else:
        return 'usuário ou senha inválidos'


@get('/logout')
def logout():
    # Logout do usuário - remove sessão ativa
    session_id = request.get_cookie(ticket.user.cookie_session_name())
    if session_id:
        ticket.user.removesession(session_id)
        response.delete_cookie(ticket.user.cookie_session_name())
        ticket.db.expire_old_sessions()
    return redirect('/login')
