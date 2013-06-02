# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

import config
import ticket

import os
from bottle import run

print ';; carregando ticket'
print ';; banco de dados = %s' % config.dbname
print ';; host = %s' % config.host
print ';; port = %s' % config.port
if config.debug:
    print ';; modo de debug ativado'

# Cria banco de dados caso arquivo não exista
if not os.path.isfile(config.dbname):
    createdb(config.dbname)

run(host=config.host, port=config.port, debug=config.debug,
    server='waitress', reloader=config.debug)