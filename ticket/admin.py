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
