import os.path
import sqlite3
from contextlib import contextmanager

from bottle import local

import ticket.tickets
from ticket.config import cfg


def get_db() -> sqlite3.Connection:
    """
    Retorna um handle de conexão de banco de dados por thread.
    """
    if not hasattr(local, "db"):
        local.db = sqlite3.connect(
            os.path.join(cfg("paths", "data"), "ticket.db"),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        # Permite acessar resultados via dict() por nome da coluna
        local.db.row_factory = sqlite3.Row
    return local.db


def get_cursor() -> sqlite3.Cursor:
    """
    Retorna um novo cursor para acesso ao banco de dados.
    """
    return get_db().cursor()


@contextmanager
def db_trans():
    """
    Abre uma transação no banco de dados e faz o commit ao finalizar o
    contexto, ou rollback caso algo falhe.
    """
    dbh = get_db()
    c = dbh.cursor()
    try:
        yield c  # Retorna novo cursor
    except Exception:
        dbh.rollback()
        raise
    finally:
        dbh.commit()


def populate_search(ticket_id: int):
    """
    Popula o índice de busca full-text para um ticket.
    """
    text = ""
    c = get_cursor()  # Utiliza transação do caller
    text += " " + ticket.tickets.ticket_title(ticket_id) + " "
    c.execute(
        """
        select comment
        from comments
        where ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        text += " " + r["comment"] + " "
    c.execute(
        """
        delete from search
        where docid = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    c.execute(
        """
        insert into search (
            docid,
            text
        )
        values (
            :ticket_id,
            :text
        )""",
        {"ticket_id": ticket_id, "text": text},
    )
