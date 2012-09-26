#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

import re
import os
import sys
import time
import getopt
import bottle
import smtplib
import psycopg2
import psycopg2.extras

import config

from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post
from email.mime.text import MIMEText

VERSION = '1.2dev'

# Cores de fundo das prioridades
priocolor = {
    1: '#FF8D8F',
    2: '#EDFF9F',
    3: '',
    4: '#6DF2B2',
    5: '#9FEFF2',
}

# Descrição das prioridades
priodesc = {
    1: '1. Ação Urgente',
    2: '2. Atenção',
    3: '3. Prioridade Normal',
    4: '4. Baixa Prioridade',
    5: '5. Baixíssima Prioridade',
}

def getdb():
    if not hasattr(local, 'db'):
        local.db = psycopg2.connect(database='ticket', user='postgres')
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
    return local.db

# Listagem de tickets
@route('/')
@view('list-tickets')
def index():
    # A página padrão exibe os tickets ordenados por prioridade
    if 'filter' not in request.query.keys():
        return redirect('/?filter=o:p')
    filter = request.query.get('filter')
    if filter.strip() == '': filter = 'o:p'

    # Redireciona ao ticket caso pesquisa seja #NNNNN
    m = re.match(r'^#(\d+)$', filter)
    if m: return redirect('/%s' % m.group(1))

    c = getdb().cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Dividindo filtro em tokens separados por espaços
    tokens = filter.strip().split()

    limit = tags = user = date = prio = ''
    search = []
    status = 'AND status = 0'
    order = 'ORDER BY datemodified DESC'

    # Abrangência dos filtros (status)
    # T: todos
    # F: fechados
    # A: abertos
    if re.match(r'^[TFA] ', filter):
        if tokens[0] == 'T': status = ''
        elif tokens[0] == 'A': status = 'AND status = 0'
        elif tokens[0] == 'F': status = 'AND status = 1'
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

        # Ordenação (o:m)
        m = re.match(r'^o:([mcfp])$', t)
        if m:
            o = m.group(1)
            if o == 'c': order = 'ORDER BY datecreated DESC'
            elif o == 'm': order = 'ORDER BY datemodified DESC'
            elif o == 'f': order = 'ORDER BY dateclosed DESC'
            elif o == 'p': order = 'ORDER BY priority ASC, datecreated ASC'
            continue

        # Usuário de criação, fechamento, modificação (u:USER)
        m = re.match(r'^u:(.+)$', t)
        if m:
            u = m.group(1)
            user = c.mogrify("""
               AND ( ( "user" = %s )
                OR ( id IN ( SELECT ticket_id FROM comments WHERE "user" = %s ) )
                OR ( id IN ( SELECT ticket_id FROM timetrack WHERE "user" = %s ) )
                OR ( id IN ( SELECT ticket_id FROM statustrack WHERE "user" = %s ) ) )
            """, (u, u, u, u))
            continue

        # Faixa de data de criação, fechamento, modificação
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1, m1, d1, y2, m2, d2 = m.groups()[1:]
            if m.group(1) == 'c': dt = 'datecreated'
            elif m.group(1) == 'm': dt = 'datemodified'
            elif m.group(1) == 'f': dt = 'dateclosed'
            date = """
                AND %s BETWEEN '%s-%s-%s 00:00:00' AND '%s-%s-%s 23:59:59'
            """ % ( dt, y1, m1, d1, y2, m2, d2 )
            continue

        # Data de criação, fechamento, modificação
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1, m1, d1 = m.groups()[1:]
            if m.group(1) == 'c': dt = 'datecreated'
            elif m.group(1) == 'm': dt = 'datemodified'
            elif m.group(1) == 'f': dt = 'dateclosed'
            date = """
                AND %s BETWEEN '%s-%s-%s 00:00:00' AND '%s-%s-%s 23:59:59'
            """ % ( dt, y1, m1, d1, y1, m1, d1 )
            continue

        # Faixa de prioridade (p:1-2)
        m = re.match(r'^p:([1-5])-([1-5])$', t)
        if m:
            p1, p2 = m.groups()
            prio = """
                AND priority BETWEEN %s AND %s
            """ % (p1, p2)
            continue

        # Prioridade (p:1)
        m = re.match(r'^p:([1-5])$', t)
        if m:
            p1 = m.group(1)
            prio = """
                AND priority = %s
            """ % (p1,)
            continue

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
            %s
    ''' % (status, searchstr, tags, user, date, prio, order, limit)

    c.execute(sql)
    tickets = []
    for ticket in c:
        ticketdict = dict(ticket)
        ticketdict['tags'] = tickettags(ticket['id'])
        tickets.append(ticketdict)

    getdb().commit()

    return dict(tickets=tickets, filter=filter, priodesc=priodesc, 
        priocolor=priocolor, tagsdesc=tagsdesc(), version=VERSION)


# Tela de novo ticket
@get('/new-ticket')
@view('new-ticket')
def newticket():
    return dict(version=VERSION)

# Salva novo ticket
@post('/new-ticket')
def newticketpost():
    assert 'title' in request.forms
    title = request.forms.title.strip()
    if title == '': return 'erro: título inválido'
    c = getdb().cursor()
    try:
        c.execute('''
            INSERT INTO TICKETS (
                title, "user"
            )
            VALUES ( %s, %s )
            RETURNING id
        ''', (title, '') )
        ticket_id = c.fetchone()[0]
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

# Exibe os detalhes de um ticket
@get('/<ticket_id:int>')
@view('show-ticket')
def showticket(ticket_id):
    c = getdb().cursor(cursor_factory=psycopg2.extras.DictCursor)

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
    tags = tickettags(ticket_id)

    # Obtém contatos
    contacts = ticketcontacts(ticket_id)

    getdb().commit()

    # Renderiza template

    return dict(ticket=ticket, comments=comments, priocolor=priocolor,
        priodesc=priodesc, timetrack=timetrack, tags=tags, contacts=contacts,
        tagsdesc=tagsdesc(), version=VERSION)

@post('/close-ticket/<ticket_id:int>')
def closeticket(ticket_id):
    c = getdb().cursor()
    try:
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
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@post('/change-title/<ticket_id:int>')
def changetitle(ticket_id):
    assert 'text' in request.forms
    title = request.forms.text.strip()
    if title == '': return 'erro: título inválido'
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE tickets
            SET title = %s
            WHERE id = %s
        ''', (title, ticket_id,))
    except:
        getdb().rollback()
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@post('/change-tags/<ticket_id:int>')
def changetags(ticket_id):
    assert 'text' in request.forms
    tags = request.forms.text
    tags = tags.strip().split()
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM tags
            WHERE ticket_id = %s
        ''', ( ticket_id, ))
        for tag in tags:
            c.execute('''
                INSERT INTO tags ( ticket_id, tag )
                VALUES ( %s, %s )
            ''', (ticket_id, tag) )
    except:
        getdb().rollback()
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@post('/change-contacts/<ticket_id:int>')
def changecontacts(ticket_id):
    assert 'contacts' in request.forms
    contacts = request.forms.contacts
    contacts = contacts.strip().split()
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM contacts
            WHERE ticket_id = %s
        ''', ( ticket_id, ))
        for contact in contacts:
            c.execute('''
                INSERT INTO contacts ( ticket_id, email )
                VALUES ( %s, %s )
            ''', (ticket_id, contact) )
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@post('/register-minutes/<ticket_id:int>')
def registerminutes(ticket_id):
    assert 'minutes' in request.forms
    if not re.match(r'^[\-0-9\.]+$', request.forms.minutes):
        return 'tempo inválido'
    minutes = float(request.forms.minutes)
    if minutes <= 0.0: return 'tempo inválido'
    c = getdb().cursor()
    try:
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
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@post('/new-note/<ticket_id:int>')
def newnote(ticket_id):
    assert 'text' in request.forms
    assert 'contacts' in request.forms
    note = request.forms.text
    contacts = request.forms.contacts.strip().split()
    if note.strip() == '': return 'nota inválida'
    c = getdb().cursor()
    try:
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
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    toemail = []
    for contact in contacts:
        if contact.startswith('#'): continue
        toemail.append(contact)

    if len(toemail) > 0:
        title = tickettitle(ticket_id)
        subject = u'#%s - %s' % (ticket_id, title)
        body = u'''
[%s] (anônimo):

%s


-- Este é um e-mail automático enviado pelo sistema ticket.
        ''' % ( time.strftime('%Y-%m-%d %H:%M'), note )

        sendmail(config.email_from, toemail, config.email_smtp,
            subject, body)

    return redirect('/%s' % ticket_id)

@post('/reopen-ticket/<ticket_id:int>')
def reopenticket(ticket_id):
    c = getdb().cursor()
    try:
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
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@post('/change-priority/<ticket_id:int>')
def changepriority(ticket_id):
    assert 'prio' in request.forms
    assert re.match(r'^[1-5]$', request.forms.prio)
    priority = int(request.forms.prio)
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE tickets
            SET priority = %s
            WHERE id = %s
        ''', (priority, ticket_id,))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)

@route('/static/:filename')
def static(filename):
    assert re.match(r'^[\w\d\-]+\.[\w\d\-]+$', filename)
    return static_file('static/%s' % filename, root='.')

def tagsdesc():
    c = getdb().cursor(cursor_factory=psycopg2.extras.DictCursor)
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

def tickettags(ticket_id):
    tags = []
    c = getdb().cursor()
    c.execute('''
        SELECT tag
        FROM tags
        WHERE ticket_id = %s
    ''', (ticket_id,))
    for r in c:
        tags.append(r[0])
    return tags

def ticketcontacts(ticket_id):
    contacts = []
    c = getdb().cursor()
    c.execute('''
        SELECT email
        FROM contacts
        WHERE ticket_id = %s
    ''', (ticket_id,))
    for r in c:
        contacts.append(r[0])
    return contacts

def tickettitle(ticket_id):
    c = getdb().cursor()
    c.execute('''
        SELECT title
        FROM tickets
        WHERE id = %s
    ''', (ticket_id,))
    title = c.fetchone()[0]
    return title

def sendmail(fromemail, toemail, smtpserver, subject, body):
    for contact in toemail:
        msg = MIMEText(body.encode('utf-8'))
        msg.set_charset('utf-8')
        msg['Subject'] = subject
        msg['From'] = fromemail
        msg['To'] = contact
        s = smtplib.SMTP(smtpserver, timeout=10)
        s.sendmail(fromemail, contact, msg.as_string())
        s.quit()

if __name__ == '__main__':

    address = '0.0.0.0'
    port = 8080
    dbpath = 'ticket.db'

    bottle.debug(True)
    run(host=address, port=port, server='auto', reloader=True)
