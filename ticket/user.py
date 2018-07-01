# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

from ticket.config import config

import ticket.db

from bottle import request, redirect
from functools import wraps
from hashlib import sha1
from uuid import uuid4

def requires_auth(f):
    # Decorator em router do Bottle para forçar autenticação do usuário
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie(cookie_session_name())
        if not session_id or not validatesession(session_id):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def requires_admin(f):
    # Decorator em router do Bottle para certificar que usuário é administrador
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie(cookie_session_name())
        if not session_id or not validatesession(session_id) or \
                not ticket.user.userisadmin(currentuser()):
            return 'não autorizado'
        return f(*args, **kwargs)
    return decorated

def cookie_session_name():
    # Retorna o nome do cookie para a sessão
    return 'ticket_session_%s' % config("port")

def validateuserdb(user, passwd):
    # Valida usuário e senha no banco de dados
    passwdsha1 = sha1(passwd.encode("UTF-8")).hexdigest()
    c = ticket.db.getcursor()
    c.execute("select username from users where username = :user "
        "and password = :passwdsha1", locals())
    r = c.fetchone()
    return bool(r)


def validatesession(session_id):
    # Valida sessão ativa no banco de dados
    c = ticket.db.getcursor()
    c.execute("select session_id from sessions where session_id = :session_id",
        locals())
    r = c.fetchone()
    return bool(r)


def userident(username):
    # Retorna nome e e-mail de usuário
    c = ticket.db.getcursor()
    c.execute("select name, email from users where username=:username",
        locals())
    return dict(c.fetchone())


def currentuser():
    # Retorna usuário corrente
    session_id = request.get_cookie(ticket.user.cookie_session_name())
    c = ticket.db.getcursor()
    c.execute("select username from sessions "
        "where session_id = :session_id", locals())
    return c.fetchone()['username']


def userisadmin(username):
    # Checa se usuário tem poderes administrativos
    c = ticket.db.getcursor()
    c.execute("select is_admin from users where username = :username",
        locals())
    return c.fetchone()['is_admin']


def removesession(session_id):
    # Remove uma sessão do banco de dados
    with ticket.db.db_trans() as c:
        c.execute("delete from sessions where session_id = :session_id", 
            locals())


def makesession(user):
    # Cria uma nova sessão no banco de dados
    with ticket.db.db_trans() as c:
        session_id = str(uuid4())
        c.execute("insert into sessions (session_id, username) "
            "values (:session_id, :user)", locals())
    return session_id