# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

import random

from hashlib import sha1
from bottle import get, view, post, request, redirect

import ticket.user
import ticket.db

import config

@get('/admin')
@view('admin')
@ticket.user.requires_auth
@ticket.user.requires_admin
def admin():
    # Tela de administração
    username = ticket.user.currentuser()
    users = []
    c = ticket.db.getcursor()
    c.execute("select username, is_admin, name, email from users "
        "order by username")
    for user in c:
        user = dict(user)
        user['name'] = user['name'] or ''
        user['email'] = user['email'] or ''
        users.append(user)
    return dict(version=ticket.VERSION, username=username, users=users, 
            userisadmin=ticket.user.userisadmin(username), features=config.features)

@get('/admin/remove-user/:username')
@ticket.user.requires_auth
@ticket.user.requires_admin
def removeuser(username):
    # Apaga um usuário
    if username == ticket.user.currentuser():
        return 'não é possível remover usuário corrente'
    with ticket.db.db_trans() as c:
        c.execute("delete from users where username = :username", locals())
    return redirect('/admin')


@get('/admin/edit-user/:username')
@view('edit-user')
@ticket.user.requires_auth
@ticket.user.requires_admin
def edituser(username):
    # Exibe tela de edição de usuários
    c = ticket.db.getcursor()
    c.execute("select name, email from users where username = :username",
        locals())
    r = c.fetchone()
    name = ''
    email = ''
    if not r:
        return 'usuário %s não encontrado!' % username
    else:
        name = r['name'] or ''
        email = r['email'] or ''
        return dict(user=username, name=name, email=email,
            username=ticket.user.currentuser(), version=ticket.VERSION,
            userisadmin=ticket.user.userisadmin(ticket.user.currentuser()))


@post('/admin/edit-user/:username')
@ticket.user.requires_auth
@ticket.user.requires_admin
def editusersave(username):
    # Salva os dados de um usuário editado
    assert 'name' in request.forms
    assert 'email' in request.forms
    name = request.forms.name.strip()
    email = request.forms.email.strip()
    with ticket.db.db_trans() as c:
        c.execute("update users set name=:name, email=:email "
            "where username=:username", locals())
    return redirect('/admin')


@post('/admin/save-new-user')
@ticket.user.requires_auth
@ticket.user.requires_admin
def newuser():
    # Cria um novo usuário
    assert 'username' in request.forms
    username = request.forms.username
    if username.strip() == '':
        return 'usuário inválido'
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    with ticket.db.db_trans() as c:
        c.execute("insert into users (username, password, is_admin ) "
            "values (:username, :sha1password, 0)", locals())
    return u'usuário %s criado com senha %s' % ( username, password )


@get('/admin/force-new-password/:username')
@ticket.user.requires_auth
@ticket.user.requires_admin
def forceuserpassword(username):
    # Reseta senha de um usuário
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    if username == ticket.user.currentuser():
        return 'não é possível forçar nova senha de usuário corrente'
    with ticket.db.db_trans() as c:
        c.execute("update users set password = :sha1password "
            "where username = :username", locals())
    return u'usuário %s teve nova senha forçada: %s' % ( username, password )


@get('/admin/change-user-admin-status/:username/:status')
@ticket.user.requires_auth
@ticket.user.requires_admin
def changeuseradminstatus(username, status):
    # Altera status de administrador de um usuário
    if username == ticket.user.currentuser():
        return 'não é possível alterar status de admin para usuário corrente'
    assert status in ( '0', '1' )
    with ticket.db.db_trans() as c:
        c.execute("update users set is_admin = :status "
            "where username = :username", locals())
    return redirect('/admin')


@get('/admin/reindex-fts')
@ticket.user.requires_auth
@ticket.user.requires_admin
def reindexfts():
    # Recria o índice de Full Text Search
    with ticket.db.db_trans() as c:
        print 'limpando índices'
        c.execute("delete from search")
        print 'iniciando recriação dos índices'
        c.execute("select id from tickets order by id")
        for r in c:
            print 'reindexando ticket #%s' % r['id']
            ticket.db.populatesearch(r['id'])
    return 'índices de full text search recriados!'