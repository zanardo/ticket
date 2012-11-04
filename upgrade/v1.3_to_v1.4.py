#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Migra o schema e dados de um banco de dados SQLite do
# ticket versão 1.3 para a versão 1.4.
# ATENÇÃO! Faça um backup antes de executar este procedimento!

import sys
import sqlite3

if len(sys.argv) < 2:
	print 'uso: %s <db>' % sys.argv[0]
	sys.exit(1)

db_name = sys.argv[1]

print ';; conectando-se ao SQLite - %s' % db_name
db = sqlite3.connect(db_name)

print ';; migrando schema da versão 1.3 para 1.4'
try:
	c = db.cursor()
	c.executescript('''
		CREATE TABLE files (
			id integer NOT NULL PRIMARY KEY,
			ticket_id integer NOT NULL,
			name text NOT NULL,
			datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
			user text NOT NULL,
			size integer NOT NULL,
			contents blob NOT NULL
		);
		CREATE INDEX idx_files_ticket_id ON files ( ticket_id );
		INSERT INTO config ( key, value ) VALUES ( 'file.maxsize', '128000' );
		ALTER TABLE users ADD COLUMN email text;
		ALTER TABLE users ADD COLUMN name text;
	''')
except:
	db.rollback()
	raise
else:
	db.commit()