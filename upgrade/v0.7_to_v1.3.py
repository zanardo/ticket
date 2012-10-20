#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Migra o schema e dados de um banco de dados SQLite do
# ticket versão 0.7 para a versão 1.3.
# O banco de dados de destino deverá ter sido criado usando
# o schema e deverá estar vazio.
# ATENÇÃO! Faça um backup antes de executar este procedimento!

import sys
import sqlite3

if len(sys.argv) < 3:
	print 'uso: %s <db-origem> <db-destino>' % sys.argv[0]
	sys.exit(1)

db_origem, db_destino = sys.argv[1:3]

db1 = sqlite3.connect(db_origem)
db2 = sqlite3.connect(db_destino)

db1.row_factory = sqlite3.Row
db1.text_factory = lambda x: unicode(x, "latin1")

print ';; migrando schema da versão 0.7 para 1.3'
c1 = db1.cursor()
c2 = db2.cursor()

print ';; importando tickets'
c1.execute('''
	SELECT ID, STATUS, TYPE, PRIO, DATECREATED, DATECLOSED,
		DATEMODIFIED, USER, TEXT
	FROM TICKET
	WHERE IDPARENT IS NULL
	ORDER BY ID
''')
for r in c1:

	title = r['TEXT']
	if len(title) > 50:
		title = title[:50] + ' ...'
	elif title.strip() == '':
		title = '(sem título)'

	dateclosed = r['DATECLOSED']

	status = r['STATUS']
	if status is None or str(status).strip() == '':
		status = 1
		dateclosed = r['DATECREATED']

	c2.execute('''
		INSERT INTO tickets ( id, title, status, priority, datecreated,
			datemodified, dateclosed, user )
		VALUES ( ?, ?, ?, ?, ?, ?, ?, ? )
	''', ( r['ID'], title, status, r['PRIO'], r['DATECREATED'],
			r['DATEMODIFIED'], dateclosed, r['USER'] ))
	c2.execute('''
		INSERT INTO comments ( ticket_id, datecreated, user, comment )
		VALUES ( ?, ?, ?, ? )
	''', ( r['ID'], r['DATECREATED'], r['USER'], r['TEXT'] ))

print ';; importando eventos'
c1.execute('''
	SELECT IDPARENT, STATUS, TYPE, PRIO, DATECREATED, DATECLOSED,
		DATEMODIFIED, USER, TEXT
	FROM TICKET
	WHERE IDPARENT IS NOT NULL
	ORDER BY IDPARENT, ID
''')
for r in c1:
	if r['TEXT'].strip() != '':
		c2.execute('''
			INSERT INTO comments ( ticket_id, datecreated, user, comment )
			VALUES ( ?, ?, ?, ? )
		''', ( r['IDPARENT'], r['DATECREATED'], r['USER'], r['TEXT'] ))
	# Fechamento
	if r['TYPE'] == 5:
		c2.execute('''
			INSERT INTO statustrack ( ticket_id, datecreated, user, status )
			VALUES ( ?, ?, ?, ? )
		''', ( r['IDPARENT'], r['DATECREATED'], r['USER'], 'close' ))
	# Reabertura
	elif r['TYPE'] == 6:
		c2.execute('''
			INSERT INTO statustrack ( ticket_id, datecreated, user, status )
			VALUES ( ?, ?, ?, ? )
		''', ( r['IDPARENT'], r['DATECREATED'], r['USER'], 'reopen' ))


db1.rollback()
db2.commit()