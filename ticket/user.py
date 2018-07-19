from typing import Dict

import ticket.db

from bottle import request, redirect
from functools import wraps
from hashlib import sha1
from uuid import uuid4


def requires_auth(f):
    """
    Decorator em router do Bottle para forçar autenticação do usuário.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie(cookie_session_name())
        if not session_id or not validate_session(session_id):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def requires_admin(f):
    """
    Decorator em router do Bottle para certificar que usuário é administrador.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie(cookie_session_name())
        if not session_id or not validate_session(session_id) or \
                not ticket.user.user_admin(current_user()):
            return "não autorizado"
        return f(*args, **kwargs)
    return decorated


def cookie_session_name() -> str:
    """
    Retorna o nome do cookie para a sessão.
    """
    return "ticket_session"


def validate_user_db(user, passwd) -> bool:
    """
    Valida usuário e senha no banco de dados.
    """
    passwdsha1 = sha1(passwd.encode("UTF-8")).hexdigest()
    c = ticket.db.get_cursor()
    c.execute("""
        select username
        from users
        where username = :user
            and password = :passwdsha1
        """, locals())
    r = c.fetchone()
    return bool(r)


def validate_session(session_id) -> bool:
    """
    Valida sessão ativa no banco de dados.
    """
    c = ticket.db.get_cursor()
    c.execute("""
        select session_id
        from sessions
        where session_id = :session_id
    """, locals())
    r = c.fetchone()
    return bool(r)


def user_ident(username) -> Dict[str, str]:
    """
    Retorna o nome e e-mail de usuário.
    """
    c = ticket.db.get_cursor()
    c.execute("""
        select name,
            email
        from users
        where username=:username
    """, locals())
    return dict(c.fetchone())


def current_user() -> str:
    """
    Retorna o usuário corrente.
    """
    session_id = request.get_cookie(ticket.user.cookie_session_name())
    c = ticket.db.get_cursor()
    c.execute("""
        select username
        from sessions
        where session_id = :session_id
    """, locals())
    return c.fetchone()["username"]


def user_admin(username) -> bool:
    """
    Checa se usuário tem poderes administrativos.
    """
    c = ticket.db.get_cursor()
    c.execute("""
        select is_admin
        from users
        where username = :username
    """, locals())
    return c.fetchone()["is_admin"]


def remove_session(session_id) -> None:
    """
    Remove uma sessão do banco de dados.
    """
    with ticket.db.db_trans() as c:
        c.execute("""
            delete from sessions
            where session_id = :session_id
        """, locals())


def make_session(user) -> str:
    """
    Cria uma nova sessão no banco de dados.
    """
    with ticket.db.db_trans() as c:
        session_id = str(uuid4())
        c.execute("""
            insert into sessions (
                session_id,
                username
            )
            values (
                :session_id,
                :user
            )
        """, locals())
    return session_id


def expire_old_sessions() -> None:
    """
    Expira sessões mais antigas que 7 dias.
    """
    with ticket.db.db_trans() as c:
        c.execute("""
            delete from sessions
            where julianday('now') - julianday(date_login) > 7
        """)


def change_password(user: str, password: str) -> None:
    """
    Altera a senha de um usuário.
    """
    passwd_sha1 = sha1(password.encode("UTF-8")).hexdigest()
    with ticket.db.db_trans() as c:
        c.execute("""
            update users
            set password = :passwd_sha1
            where username = :user
        """, locals())
