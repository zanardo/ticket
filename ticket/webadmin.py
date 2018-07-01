import random

from hashlib import sha1
from bottle import get, view, post, request, redirect

import ticket.user
import ticket.db
from ticket.context import TemplateContext
from ticket.log import log

@get('/admin')
@view('admin')
@ticket.user.requires_auth
@ticket.user.requires_admin
def admin():
    # Tela de administração
    ctx = TemplateContext()
    ctx.users = []
    c = ticket.db.get_cursor()
    c.execute("select username, is_admin, name, email from users "
        "order by username")
    for user in c:
        user = dict(user)
        user['name'] = user['name'] or ''
        user['email'] = user['email'] or ''
        ctx.users.append(user)
    return dict(ctx=ctx)

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
    ctx = TemplateContext()
    ctx.user = username
    c = ticket.db.get_cursor()
    c.execute("select name, email from users where username = :username",
        locals())
    r = c.fetchone()
    ctx.name = ''
    ctx.email = ''
    if not r:
        return 'usuário %s não encontrado!' % username
    else:
        ctx.name = r['name'] or ''
        ctx.email = r['email'] or ''
        return dict(ctx=ctx)


@post('/admin/edit-user/:username')
@ticket.user.requires_auth
@ticket.user.requires_admin
def editusersave(username):
    # Salva os dados de um usuário editado
    assert 'name' in request.forms
    assert 'email' in request.forms
    name = request.forms.get("name").strip()
    email = request.forms.get("email").strip()
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
    username = request.forms.get("username")
    if username.strip() == '':
        return 'usuário inválido'
    password = str(int(random.random() * 999999))
    sha1password = sha1(password.encode("UTF-8")).hexdigest()
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
        log.info("limpando índices")
        c.execute("delete from search")
        log.info('iniciando recriação dos índices')
        c.execute("select id from tickets order by id")
        for r in c:
            log.debug('reindexando ticket #%s', r['id'])
            ticket.db.populatesearch(r['id'])
    return 'índices de full text search recriados!'
