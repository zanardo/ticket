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

@route('/')
def index():
    # A página padrão exibe os tickets ordenados por prioridade
    if 'filter' not in request.query.keys():
        return redirect('/?filter=o:p')

    filter = request.query.get('filter') or ''

    # Redireciona ao ticket caso pesquisa seja #NNNNN
    m = re.match(r'^#(\d+)$', filter)
    if m:
        return redirect('/%s' % m.group(1))

    c = db.cursor()

    # Dividindo filtro em tokens separados por espaços
    tokens = filter.strip().split()

    search = []
    limit = ''
    status = 'AND status = 0'
    tags = ''
    order = 'ORDER BY datemodified DESC'
    user = ''
    date = ''

    # Abrangência dos filtros (status)
    # T: todos
    # F: fechados
    # A: abertos
    if re.match(r'^[TFA] ', filter):
        if tokens[0] == 'T':
            status = ''
        elif tokens[0] == 'A':
            status = 'AND status = 0'
        elif tokens[0] == 'F':
            status = 'AND status = 1'
        tokens.pop(0)   # Removendo primeiro item

    for t in tokens:
        # Limite de resultados (l:NNN)
        m = re.match(r'^l:(\d+)$', t)
        if m:
            limit = 'LIMIT %s' % m.group(1)
            continue
        # Palavra-chave (t:TAG)
        m = re.match(r'^t:(.+)$', t)
        if m:
            tags += c.mogrify(
                'AND id IN ( SELECT ticket_id FROM tags WHERE tag  = %s ) ',
                (m.group(1),))
            continue
        # Ordenação
        m = re.match(r'^o:([mcfp])$', t)
        if m:
            o = m.group(1)
            if o == 'c':
                order = 'ORDER BY datecreated DESC'
            elif o == 'm':
                order = 'ORDER BY datemodified DESC'
            elif o == 'f':
                order = 'ORDER BY dateclosed DESC'
            elif o == 'p':
                order = 'ORDER BY priority ASC, datecreated ASC'
        # Usuário de criação, fechamento, modificação
        m = re.match(r'^u:(.+)$', t)
        if m:
            u = m.group(1)
            user = c.mogrify("""
               AND ( ( "user" = %s )
                OR ( id IN ( SELECT ticket_id FROM comments WHERE "user" = %s ) )
                OR ( id IN ( SELECT ticket_id FROM timetrack WHERE "user" = %s ) )
                OR ( id IN ( SELECT ticket_id FROM statustrack WHERE "user" = %s ) ) )
            """, (u, u, u, u))
        # Faixa de data de criação, fechamento, modificação
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1 = m.group(2)
            m1 = m.group(3)
            d1 = m.group(4)
            y2 = m.group(5)
            m2 = m.group(6)
            d2 = m.group(7)
            if m.group(1) == 'c':
                dt = 'datecreated'
            elif m.group(1) == 'm':
                dt = 'datemodified'
            elif m.group(1) == 'f':
                dt = 'dateclosed'
            date = """
                AND %s BETWEEN '%s-%s-%s 00:00:00' AND '%s-%s-%s 23:59:59'
            """ % ( dt, y1, m1, d1, y2, m2, d2 )
        # Data de criação, fechamento, modificação
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1 = m.group(2)
            m1 = m.group(3)
            d1 = m.group(4)
            if m.group(1) == 'c':
                dt = 'datecreated'
            elif m.group(1) == 'm':
                dt = 'datemodified'
            elif m.group(1) == 'f':
                dt = 'dateclosed'
            date = """
                AND %s BETWEEN '%s-%s-%s 00:00:00' AND '%s-%s-%s 23:59:59'
            """ % ( dt, y1, m1, d1, y1, m1, d1 )
        # Texto para busca
        search.append(t)

    searchstr = ''
    if len(search) > 0:
        s = ' '.join(search)
        searchstr = c.mogrify("""
            AND ( id IN ( SELECT id FROM tickets WHERE to_tsvector('portuguese', title) @@ plainto_tsquery(%s))
                OR id IN ( SELECT ticket_id FROM comments WHERE to_tsvector('portuguese', comment) @@ plainto_tsquery(%s) ) )
        """, (s, s))

    sql = '''
        SELECT *
        FROM tickets
        WHERE ( 1 = 1 )
            %s
            %s
            %s
            %s
            %s
            %s
            %s
    ''' % (
        status,
        searchstr,
        tags,
        user,
        date,
        order,
        limit,
    )

    response.content_type = 'text/plain; charset=utf-8'
    return sql


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

    # Obtém dados do ticket

    c.execute('''
        SELECT *
        FROM tickets
        WHERE id = %s
    ''', ( ticket_id, ) )
    ticket = c.fetchone()

    # Obtém notas, mudanças de status e registro de tempo

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

    # Obtém resumo de tempo trabalhado

    timetrack = []
    c.execute('''
        SELECT "user", SUM(minutes) AS minutes
        FROM timetrack
        WHERE ticket_id = %s
        GROUP BY "user"
        ORDER BY "user"
    ''', (ticket_id,))
    for r in c:
        timetrack.append(r)

    # Obtém palavras-chave

    tags = []
    c.execute('''
        SELECT tag
        FROM tags
        WHERE ticket_id = %s
    ''', (ticket_id,))
    for r in c:
        tags.append(r['tag'])

    # Obtém contatos

    contacts = []
    c.execute('''
        SELECT email
        FROM contacts
        WHERE ticket_id = %s
    ''', (ticket_id,))
    for r in c:
        contacts.append(r['email'])

    # Renderiza template

    return dict(ticket=ticket, comments=comments, priocolor=priocolor,
        priodesc=priodesc, timetrack=timetrack, tags=tags, contacts=contacts,
        tagsdesc=tagsdesc())

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

@post('/change-tags/<ticket_id:int>')
def changetags(ticket_id):
    c = db.cursor()
    tags = request.forms.get('text') or ''
    tags = tags.strip().split()
    c.execute('''
        DELETE FROM tags
        WHERE ticket_id = %s
    ''', ( ticket_id, ))
    for tag in tags:
        c.execute('''
            INSERT INTO tags ( ticket_id, tag )
            VALUES ( %s, %s )
        ''', (ticket_id, tag) )
    db.commit()
    return redirect('/%s' % ticket_id)

@post('/change-contacts/<ticket_id:int>')
def changecontacts(ticket_id):
    c = db.cursor()
    contacts = request.forms.get('contacts') or ''
    contacts = contacts.strip().split()
    c.execute('''
        DELETE FROM contacts
        WHERE ticket_id = %s
    ''', ( ticket_id, ))
    for contact in contacts:
        c.execute('''
            INSERT INTO contacts ( ticket_id, email )
            VALUES ( %s, %s )
        ''', (ticket_id, contact) )
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

@post('/new-note/<ticket_id:int>')
def newnote(ticket_id):
    c = db.cursor()
    note = request.forms.get('text')
    if note.strip() == '':
        return 'nota inválida'
    c.execute('''
        INSERT INTO comments (
            ticket_id, "user", comment )
        VALUES ( %s, %s, %s )
    ''', (ticket_id, 'anônimo', note))
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

@post('/change-priority/<ticket_id:int>')
def changepriority(ticket_id):
    c = db.cursor()
    priority = int(request.forms.get('prio'))
    assert(priority in (1,2,3,4,5))
    c.execute('''
        UPDATE tickets
        SET priority = %s
        WHERE id = %s
    ''', (priority, ticket_id,))
    db.commit()
    return redirect('/%s' % ticket_id)

@route('/static/:filename')
def static(filename):
    if not re.match(r'^[\w\d\-]+\.[\w\d\-]+$', filename):
        return 'invalid filename'
    return static_file('static/%s' % filename, root='.')

def tagsdesc():
    c = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('''
        SELECT tag, description, bgcolor, fgcolor
        FROM tagsdesc
    ''')
    tagdesc = {}
    for r in c:
        tagdesc[r['tag']] = {
            'description': r['description'],
            'bgcolor': r['bgcolor'],
            'fgcolor': r['fgcolor']
        }
    return tagdesc

if __name__ == '__main__':

    address = '0.0.0.0'
    port = 8080
    dbpath = 'ticket.db'

    bottle.debug(True)
    run(host=address, port=port, server='auto', reloader=True)
