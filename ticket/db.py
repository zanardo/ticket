# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

from bottle import local
from contextlib import contextmanager
import sqlite3

import ticket.tickets

import config

def getdb():
    # Retorna um handle de conexão de banco de dados por thread
    if not hasattr(local, 'db'):
        local.db = sqlite3.connect(config.dbname,
                                   detect_types=sqlite3.PARSE_DECLTYPES)
        # Permite acessar resultados via dict() por nome da coluna
        local.db.row_factory = sqlite3.Row
    return local.db

def getcursor():
    # Retorna um novo cursor para acesso ao banco de dados
    return getdb().cursor()

@contextmanager
def db_trans():
    # Abre uma transação no banco de dados e faz o commit ao
    # finalizar o contexto, ou rollback caso algo falhe.
    dbh = getdb()
    c = dbh.cursor()
    try:
        yield c     # Retorna novo cursor
    except:
        dbh.rollback()
        raise
    finally:
        dbh.commit()

def expire_old_sessions():
    # Expira sessões mais antigas que 7 dias
    with db_trans() as c:
        c.execute("delete from sessions "
            "where julianday('now') - julianday(date_login) > 7")

def createdb(dbname):
    # Cria o banco de dados caso arquivo não exista
    print ';; criando banco de dados %s' % dbname
    db = sqlite3.connect(dbname)
    fp = file('schema.sql', 'r')
    sql = "\n".join(fp.readlines())
    fp.close()
    c = db.cursor()
    c.executescript(sql)
    db.commit()
    db.close()
    print ';; banco de dados vazio criado com sucesso!'
    print ';; o primeiro login deverá ser feito com:'
    print ';; usuario: admin     senha: admin'

def populatesearch(ticket_id):
    # Popula o índice de busca full-text para um ticket
    text = ''
    c = getcursor()     # Utiliza transação do caller
    text += ' ' + ticket.tickets.tickettitle(ticket_id) + ' '
    c.execute("select comment from comments "
        "where ticket_id = :ticket_id", locals())
    for r in c:
        text += ' ' + r['comment'] + ' '
    c.execute("delete from search where docid = :ticket_id", locals())
    c.execute("insert into search ( docid, text ) "
        "values ( :ticket_id, :text )", locals())

