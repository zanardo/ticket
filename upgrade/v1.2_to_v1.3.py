#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Migra o schema e dados de um banco de dados SQLite do
# ticket versão 1.2 para a versão 1.3.
# ATENÇÃO! Faça um backup antes de executar este procedimento!

import sys
import sqlite3

if len(sys.argv) < 2:
	print 'uso: %s <db>' % sys.argv[0]
	sys.exit(1)

db_name = sys.argv[1]

print ';; conectando-se ao SQLite - %s' % db_name
db = sqlite3.connect(db_name)

print ';; migrando schema da versão 1.2 para 1.3'
try:
	c = db.cursor()
	# Tickets restritos para administradores
	c.execute('''
		ALTER TABLE tickets
		ADD COLUMN admin_only integer NOT NULL DEFAULT ( 0 )
	''')
	c.execute('''
		CREATE INDEX idx_tickets_admin_only ON tickets ( admin_only )
	''')
	# Data de previsão de solução de tickets
	c.execute('''
		ALTER TABLE tickets
		ADD COLUMN datedue timestamp
	''')
	c.execute('''
		CREATE INDEX idx_tickets_datedue ON tickets ( datedue )
	''')
except:
	db.rollback()
	raise
else:
	db.commit()