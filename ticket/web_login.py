from bottle import get, view, redirect, request, post, response
from hashlib import sha1

import ticket.user
import ticket.db
from ticket import __version__
from ticket.context import TemplateContext

# Tela de login
@get('/login')
@view('login')
def login():
    # Retorna tela de login
    return dict(version=__version__)


# Valida login
@post('/login')
def validatelogin():
    # Valida login do usuário
    assert 'user' in request.forms
    assert 'passwd' in request.forms
    user = request.forms.get("user")
    passwd = request.forms.get("passwd")
    if ticket.user.validate_user_db(user, passwd):
        session_id = ticket.user.make_session(user)
        response.set_cookie(ticket.user.cookie_session_name(), session_id)
        return redirect('/')
    else:
        return 'usuário ou senha inválidos'


@get('/logout')
def logout():
    # Logout do usuário - remove sessão ativa
    session_id = request.get_cookie(ticket.user.cookie_session_name())
    if session_id:
        ticket.user.remove_session(session_id)
        response.delete_cookie(ticket.user.cookie_session_name())
        ticket.db.expire_old_sessions()
    return redirect('/login')


@get('/change-password')
@ticket.user.requires_auth
@view('change-password')
def changepassword():
    # Tela de alteração de senha do usuário
    return dict(ctx=TemplateContext())


@post('/change-password')
@ticket.user.requires_auth
def changepasswordsave():
    # Altera a senha do usuário
    assert 'oldpasswd' in request.forms
    assert 'newpasswd' in request.forms
    assert 'newpasswd2' in request.forms
    oldpasswd = request.forms.get("oldpasswd")
    newpasswd = request.forms.get("newpasswd")
    newpasswd2 = request.forms.get("newpasswd2")
    username = ticket.user.current_user()
    if not ticket.user.validate_user_db(username, oldpasswd):
        return 'senha atual inválida!'
    if newpasswd.strip() == '' or newpasswd2.strip() == '':
        return 'nova senha inválida!'
    if newpasswd != newpasswd2:
        return 'confirmação de nova senha diferente de nova senha!'
    passwdsha1 = sha1(newpasswd.encode("UTF-8")).hexdigest()
    with ticket.db.db_trans() as c:
        c.execute("update users set password = :passwdsha1 "
            "where username = :username", locals())
    return redirect('/')