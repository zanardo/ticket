from functools import wraps
from typing import Dict
from uuid import uuid4

from bottle import redirect, request

import ticket.auth
from ticket import db
from ticket.utils import hash_password


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
        if (
            not session_id
            or not validate_session(session_id)
            or not ticket.auth.user_admin(current_user())
        ):
            return "não autorizado"
        return f(*args, **kwargs)

    return decorated


def cookie_session_name() -> str:
    """
    Retorna o nome do cookie para a sessão.
    """
    return "ticket_session"


def validate_user_db(user: str, passwd: str) -> bool:
    """
    Valida usuário e senha no banco de dados.
    """
    c = db.get_cursor()
    c.execute(
        """
        select username
        from users
        where username = :user
            and password = :passwdsha1
        """,
        {"user": user, "passwdsha1": hash_password(passwd)},
    )
    r = c.fetchone()
    return bool(r)


def validate_session(session_id: str) -> bool:
    """
    Valida sessão ativa no banco de dados.
    """
    c = db.get_cursor()
    c.execute(
        """
        select session_id
        from sessions
        where session_id = :session_id
    """,
        {"session_id": session_id},
    )
    r = c.fetchone()
    return bool(r)


def user_ident(username: str) -> Dict[str, str]:
    """
    Retorna o nome e e-mail de usuário.
    """
    c = db.get_cursor()
    c.execute(
        """
        select name,
            email
        from users
        where username=:username
    """,
        {"username": username},
    )
    return dict(c.fetchone())


def current_user() -> str:
    """
    Retorna o usuário corrente.
    """
    session_id = request.get_cookie(ticket.auth.cookie_session_name())
    c = db.get_cursor()
    c.execute(
        """
        select username
        from sessions
        where session_id = :session_id
    """,
        {"session_id": session_id},
    )
    return c.fetchone()["username"]


def user_admin(username: str) -> bool:
    """
    Checa se usuário tem poderes administrativos.
    """
    c = db.get_cursor()
    c.execute(
        """
        select is_admin
        from users
        where username = :username
    """,
        {"username": username},
    )
    return c.fetchone()["is_admin"]


def remove_session(session_id: str) -> None:
    """
    Remove uma sessão do banco de dados.
    """
    with db.db_trans() as c:
        c.execute(
            """
            delete from sessions
            where session_id = :session_id
        """,
            {"session_id": session_id},
        )


def make_session(user: str) -> str:
    """
    Cria uma nova sessão no banco de dados.
    """
    with db.db_trans() as c:
        session_id = str(uuid4())
        c.execute(
            """
            insert into sessions (
                session_id,
                username
            )
            values (
                :session_id,
                :user
            )
        """,
            {"session_id": session_id, "user": user},
        )
    return session_id


def expire_old_sessions():
    """
    Expira sessões mais antigas que 7 dias.
    """
    with db.db_trans() as c:
        c.execute(
            """
            delete from sessions
            where julianday('now') - julianday(date_login) > 7
        """
        )


def change_password(user: str, password: str) -> None:
    """
    Altera a senha de um usuário.
    """
    with db.db_trans() as c:
        c.execute(
            """
            update users
            set password = :passwd_sha1
            where username = :user
        """,
            {"passwd_sha1": hash_password(password), "user": user},
        )
