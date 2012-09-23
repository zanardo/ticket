#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#

import re
import os
import sys
import getopt
import bottle
import psycopg2
import psycopg2.extras

from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

priocolor = {
    1: '#FF8D8F',
    2: '#EDFF9F',
    3: '',
    4: '#6DF2B2',
    5: '#9FEFF2',
}

priodesc = {
    1: '1. Ação Urgente',
    2: '2. Atenção',
    3: '3. Prioridade Normal',
    4: '4. Baixa Prioridade',
    5: '5. Baixíssima Prioridade',
}

db = psycopg2.connect(database='ticket', user='postgres')
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

@get('/new-ticket')
@view('new-ticket')
def newticket():
    return dict()

@post('/new-ticket')
def newticketpost():
    title = request.forms.get('title')
    c = db.cursor()
    c.execute('''
        INSERT INTO TICKETS (
            title, "user"
        )
        VALUES ( %s, %s )
        RETURNING id
    ''', (title, '') )
    ticket_id = c.fetchone()[0]
    db.commit()
    return redirect('/%s' % ticket_id)

@get('/<ticket_id:int>')
@view('show-ticket')
def showticket(ticket_id):
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('''
        SELECT *
        FROM tickets
        WHERE id = %s
    ''', ( ticket_id, ) )
    ticket = c.fetchone()
    c.execute('''
        SELECT *
        FROM (
          SELECT datecreated
            , "user"
            , CASE status WHEN \'close\' THEN \'fechado\' WHEN \'reopen\' THEN \'reaberto\' END AS comment
            , 1 AS negrito
            , 0 AS minutes
          FROM statustrack
          WHERE ticket_id = %s
          UNION ALL
          SELECT datecreated
            , "user"
            , comment
            , 0 AS negrito
            , 0 AS minutes
          FROM comments
          WHERE ticket_id = %s
          UNION ALL
          SELECT datecreated
            , "user"
            , minutes || \' minutos trabalhados\'
            , 1 AS negrito
            , minutes
          FROM timetrack
          WHERE ticket_id = %s
        ) AS t
        ORDER BY datecreated
    ''', ( ticket_id, ticket_id, ticket_id ) )
    comments = []
    for r in c:
        comments.append(r)
    return dict(ticket=ticket, comments=comments, priocolor=priocolor,
        priodesc=priodesc)

@post('/close-ticket/<ticket_id:int>')
def closeticket(ticket_id):
    c = db.cursor()
    c.execute('''
        UPDATE tickets
        SET status = 1,
            dateclosed = NOW(),
            datemodified = NOW()
        WHERE id = %s
    ''', (ticket_id,))
    c.execute('''
        INSERT INTO statustrack (
            ticket_id, "user", status
        )
        VALUES (
            %s, %s, 'close')
    ''', (ticket_id, 'anônimo'))
    db.commit()
    return redirect('/%s' % ticket_id)

@post('/change-title/<ticket_id:int>')
def changetitle(ticket_id):
    c = db.cursor()
    title = request.forms.get('text') or '(sem título)'
    c.execute('''
        UPDATE tickets
        SET title = %s
        WHERE id = %s
    ''', (title, ticket_id,))
    db.commit()
    return redirect('/%s' % ticket_id)

@post('/register-minutes/<ticket_id:int>')
def registerminutes(ticket_id):
    c = db.cursor()
    minutes = float(request.forms.get('minutes'))
    if minutes <= 0:
        return 'tempo inválido'
    c.execute('''
        INSERT INTO timetrack (
            ticket_id, "user", minutes )
        VALUES ( %s, %s, %s )
    ''', (ticket_id, 'anônimo', minutes))
    c.execute('''
        UPDATE tickets
        SET datemodified = NOW()
        WHERE id = %s
    ''', (ticket_id,))
    db.commit()
    return redirect('/%s' % ticket_id)

@post('/reopen-ticket/<ticket_id:int>')
def reopenticket(ticket_id):
    c = db.cursor()
    c.execute('''
        UPDATE tickets
        SET status = 0,
            dateclosed = NULL,
            datemodified = NOW()
        WHERE id = %s
    ''', (ticket_id,))
    c.execute('''
        INSERT INTO statustrack (
            ticket_id, "user", status
        )
        VALUES (
            %s, %s, 'reopen')
    ''', (ticket_id, 'anônimo'))
    db.commit()
    return redirect('/%s' % ticket_id)

@route('/static/:filename')
def static(filename):
    if not re.match(r'^[\w\d\-]+\.[\w\d\-]+$', filename):
        return 'invalid filename'
    return static_file('static/%s' % filename, root='.')

if __name__ == '__main__':

    address = '0.0.0.0'
    port = 8080
    dbpath = 'ticket.db'

    bottle.debug(True)
    run(host=address, port=port, server='auto', reloader=True)
