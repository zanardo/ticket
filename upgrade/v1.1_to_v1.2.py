#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Importa os dados de um banco de dados em PostgreSQL para
# um banco de dados SQLite.
# Criar o banco de dados ticket.db através do schema.sql:
# sqlite3 ticket.db < schema.sql

import decimal
import datetime
import psycopg2
import psycopg2.extras
import sqlite3

print ';; conectando-se ao PostgreSQL...'
db1 = psycopg2.connect(database='ticket', host='localhost', user='postgres')
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

print ';; conectando-se ao SQLite'
db2 = sqlite3.connect('ticket.db')

# Importação inicial para SQLite

tables = ('tickets', 'comments', 'tags', 'tagsdesc', 'timetrack', 
	'statustrack', 'contacts' )

for table in tables:
	print ';; migrando dados da tabela %s' % table
	c1 = db1.cursor()
	c1.execute("SELECT * FROM %s" % (table,))
	for r in c1:
		c2 = db2.cursor()
		sql = "INSERT INTO %s VALUES ( %s )" % (table,
			','.join(map(lambda x: '?', range(len(r)))))
		def transl(x):
			n = []
			for i in x:
				if type(i) is decimal.Decimal:
					i = float(i)
				elif type(i) is datetime.datetime:
					i = i.strftime("%Y-%m-%d %H:%M:%S")
				n.append(i)
			return n
		v = transl(r)
		print sql, v
		c2.execute(sql, v)

db1.rollback()
db1.close()

# Mudanças adicionais para esta versão

db2.commit()
