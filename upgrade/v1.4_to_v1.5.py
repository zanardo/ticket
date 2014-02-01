# -*- coding: utf-8 -*-
# Migra o schema e dados de um banco de dados SQLite do
# ticket versão 1.4 para a versão 1.5.
# ATENÇÃO! Faça um backup antes de executar este procedimento!

import sys
import sqlite3

if len(sys.argv) < 2:
	print 'uso: %s <db>' % sys.argv[0]
	sys.exit(1)

db_name = sys.argv[1]

print ';; conectando-se ao SQLite - %s' % db_name
db = sqlite3.connect(db_name)

print ';; migrando schema da versão 1.4 para 1.5'
try:
	c = db.cursor()
	c.executescript('''
		CREATE TABLE features (
			feature text NOT NULL PRIMARY KEY
		);
	''')
except:
	db.rollback()
	raise
else:
	db.commit()