import sqlite3
from contextlib import contextmanager

from bottle import local

import ticket.tickets
from ticket.config import config


def get_db():
    """
    Retorna um handle de conexão de banco de dados por thread.
    """
    if not hasattr(local, "db"):
        local.db = sqlite3.connect(
            config("dbname"),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # Permite acessar resultados via dict() por nome da coluna
        local.db.row_factory = sqlite3.Row
    return local.db


def getcursor():
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
        yield c     # Retorna novo cursor
    except Exception:
        dbh.rollback()
        raise
    finally:
        dbh.commit()


def expire_old_sessions():
    """
    Expira sessões mais antigas que 7 dias.
    """
    with db_trans() as c:
        c.execute("""
            delete from sessions
            where julianday('now') - julianday(date_login) > 7
        """)


def populatesearch(ticket_id):
    """
    Popula o índice de busca full-text para um ticket.
    """
    text = ""
    c = getcursor()     # Utiliza transação do caller
    text += " " + ticket.tickets.tickettitle(ticket_id) + " "
    c.execute("""
        select comment
        from comments
        where ticket_id = :ticket_id
    """, locals())
    for r in c:
        text += " " + r["comment"] + " "
    c.execute("""
        delete from search
        where docid = :ticket_id
    """, locals())
    c.execute("""
        insert into search (
            docid,
            text
        )
        values (
            :ticket_id,
            :text
        )""", locals())
