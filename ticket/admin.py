from hashlib import sha1

from ticket import db
from ticket.models import User


def all_users() -> list[User]:
    """
    Retorna a lista de todos os usuários com seus dados, para tela de
    administração.
    """
    users: list[User] = []
    with db.db_trans() as c:
        c.execute(
            """
            select username,
                is_admin,
                name,
                email
            from users
            order by username
            """
        )
        for row in c:
            users.append(
                User(
                    username=row["username"],
                    is_admin=row["is_admin"],
                    name=row["name"],
                    email=row["email"],
                )
            )
    return users


def user_remove(username: str):
    """
    Remove um usuário.
    """
    with db.db_trans() as c:
        c.execute(
            """
            delete from users
            where username = :username
            """,
            {"username": username},
        )


def user(username: str) -> User:
    """
    Retorna os dados de um usuário específico.
    """
    with db.db_trans() as c:
        c.execute(
            """
            select username,
                is_admin,
                name,
                email
            from users
            where username = :username
            """,
            {"username": username},
        )
        row = c.fetchone()
        if not row:
            raise ValueError(f"usuário {username} não encontrado!")
        return User(
            username=row["username"],
            is_admin=row["is_admin"],
            name=row["name"],
            email=row["email"],
        )


def user_save(user: User):
    """
    Salva os dados de um usuário.
    """
    with db.db_trans() as c:
        c.execute(
            """
            update users
            set name = :name
                , email = :email
                , is_admin = :is_admin
            where username = :username
            """,
            {
                "name": user.name,
                "email": user.email,
                "is_admin": user.is_admin,
                "username": user.username,
            },
        )


def user_new(user: User, password: str):
    """
    Salva um novo usuário.
    """
    password = sha1(password.encode("UTF-8")).hexdigest()
    with db.db_trans() as c:
        c.execute(
            """
            insert into users (
                username,
                password,
                is_admin
            )
            values (
                :username,
                :password,
                0
            )
            """,
            {
                "username": user.username,
                "password": password,
                "is_admin": user.is_admin,
            },
        )


def user_password_save(username: str, password: str):
    """
    Salva uma nova senha para um usuário.
    """
    password = sha1(password.encode("UTF-8")).hexdigest()
    with db.db_trans() as c:
        c.execute(
            """
            update users
            set password = :password
            where username = :username
            """,
            {"password": password, "username": username},
        )
