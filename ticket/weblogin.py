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


@get('/change-password')
@ticket.user.requires_auth
@view('change-password')
def changepassword():
    # Tela de alteração de senha do usuário
    username = ticket.user.currentuser()
    return dict(username=username, version=ticket.VERSION,
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
