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

import config

import sqlite3

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