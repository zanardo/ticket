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
import random
import smtplib
import psycopg2
import psycopg2.extras

from uuid import uuid4
from hashlib import sha1
from functools import wraps
from email.mime.text import MIMEText
from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

import config
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

# Nome do dia da semana
weekdays = {
    0: 'domingo',
    1: 'segunda-feira',
    2: 'terça-feira',
    3: 'quarta-feira',
    4: 'quinta-feira',
    5: 'sexta-feira',
    6: 'sábado'
}

def getdb():
    if not hasattr(local, 'db'):
        local.db = psycopg2.connect(database=config.db_name,
            user=config.db_user, password=config.db_passwd)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
    return local.db

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie('ticket_session')
        if not session_id or not validatesession(session_id):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def requires_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie('ticket_session')
        if not session_id or not validatesession(session_id) or \
                not userisadmin(currentuser()):
            return 'não autorizado'
        return f(*args, **kwargs)
    return decorated

########################################################################################
# Roteamento de URIs
########################################################################################


# Listagem de tickets
@route('/')
@view('list-tickets')
@requires_auth
def index():
    # A página padrão exibe os tickets ordenados por prioridade
    if 'filter' not in request.query.keys():
        return redirect('/?filter=o:p g:p')
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
    group = ''

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
        orderdate = 'datemodified'
        m = re.match(r'^o:([mcfp])$', t)
        if m:
            o = m.group(1)
            if o == 'c':
                order = 'ORDER BY datecreated DESC'
                orderdate = 'datecreated'
            elif o == 'm':
                order = 'ORDER BY datemodified DESC'
                orderdate = 'datemodified'
            elif o == 'f':
                order = 'ORDER BY dateclosed DESC'
                status = 'AND status = 1'
                orderdate = 'dateclosed'
            elif o == 'p':
                order = 'ORDER BY priority ASC, datecreated ASC'
                orderdate = ''
            continue

        # Agrupamento (g:[dp])
        m = re.match(r'^g:([dp])$', t)
        if m:
            g = m.group(1)
            if g == 'p':
                group = 'priority'
            elif g == 'd':
                group = 'date'
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

    username = currentuser()
    return dict(tickets=tickets, filter=filter, priodesc=priodesc, 
        priocolor=priocolor, tagsdesc=tagsdesc(), version=VERSION,
        username=username, userisadmin=userisadmin(username), 
        orderdate=orderdate, weekdays=weekdays, group=group)


# Tela de login
@get('/login')
@view('login')
def login():
    return dict(version=VERSION)


# Valida login
@post('/login')
def validatelogin():
    assert 'user' in request.forms
    assert 'passwd' in request.forms
    user = request.forms.user
    passwd = request.forms.passwd
    v = validateuserdb(user, passwd)
    if not v: return 'usuário ou senha inválidos'
    else:
        session_id = makesession(user)
        response.set_cookie("ticket_session", session_id)
        return redirect('/')


@get('/logout')
def logout():
    session_id = request.get_cookie('ticket_session')
    if session_id:
        removesession(session_id)
        response.delete_cookie('ticket_session')
    return redirect('/login')


# Tela de novo ticket
@get('/new-ticket')
@view('new-ticket')
@requires_auth
def newticket():
    username = currentuser()
    return dict(version=VERSION, username=username,
        userisadmin=userisadmin(username))


# Salva novo ticket
@post('/new-ticket')
@requires_auth
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
        ''', (title, currentuser()) )
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
@requires_auth
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

    username = currentuser()
    return dict(ticket=ticket, comments=comments, priocolor=priocolor,
        priodesc=priodesc, timetrack=timetrack, tags=tags, contacts=contacts,
        tagsdesc=tagsdesc(), version=VERSION, username=username,
        userisadmin=userisadmin(username))


@post('/close-ticket/<ticket_id:int>')
@requires_auth
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
        ''', (ticket_id, currentuser()))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/change-title/<ticket_id:int>')
@requires_auth
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
@requires_auth
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
@requires_auth
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
@requires_auth
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
        ''', (ticket_id, currentuser(), minutes))
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
@requires_auth
def newnote(ticket_id):
    assert 'text' in request.forms
    assert 'contacts' in request.forms
    note = request.forms.text
    contacts = request.forms.contacts.strip().split()
    if note.strip() == '': return 'nota inválida'

    toemail = []
    for contact in contacts:
        if contact.startswith('#'): continue
        toemail.append(contact)
    if len(toemail) > 0:
        note += u' [Notificação enviada para: %s]' % (
            ', '.join(toemail)
        )

    c = getdb().cursor()
    try:
        c.execute('''
            INSERT INTO comments (
                ticket_id, "user", comment )
            VALUES ( %s, %s, %s )
        ''', (ticket_id, currentuser(), note))
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

    if len(toemail) > 0:
        title = tickettitle(ticket_id)
        subject = u'#%s - %s' % (ticket_id, title)
        body = u'''
[%s] (%s):

%s


-- Este é um e-mail automático enviado pelo sistema ticket.
        ''' % ( time.strftime('%Y-%m-%d %H:%M'), currentuser(), note )

        sendmail(config.email_from, toemail, config.email_smtp,
            subject, body)

    return redirect('/%s' % ticket_id)


@post('/reopen-ticket/<ticket_id:int>')
@requires_auth
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
        ''', (ticket_id, currentuser()))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/change-priority/<ticket_id:int>')
@requires_auth
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


@get('/change-password')
@requires_auth
@view('change-password')
def changepassword():
    username = currentuser()
    return dict(username=username, version=VERSION,
        userisadmin=userisadmin(username))


@post('/change-password')
@requires_auth
def changepasswordsave():
    assert 'oldpasswd' in request.forms
    assert 'newpasswd' in request.forms
    assert 'newpasswd2' in request.forms
    oldpasswd = request.forms.oldpasswd
    newpasswd = request.forms.newpasswd
    newpasswd2 = request.forms.newpasswd2
    username = currentuser()
    if not validateuserdb(username, oldpasswd):
        return 'senha atual inválida!'
    if newpasswd.strip() == '' or newpasswd2.strip() == '':
        return 'nova senha inválida!'
    if newpasswd != newpasswd2:
        return 'confirmação de nova senha diferente de nova senha!'
    passwdsha1 = sha1(newpasswd).hexdigest()
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE users
            SET password = %s
            WHERE username = %s
        ''', (passwdsha1, username))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return redirect('/')


@get('/admin')
@view('admin')
@requires_auth
@requires_admin
def admin():
    username = currentuser()
    users = []
    c = getdb().cursor()
    c.execute('''
        SELECT username, is_admin
        FROM users
        ORDER BY username
    ''')
    for user in c:
        users.append({'username': user[0], 'is_admin': user[1]})
    return dict(version=VERSION, username=username, users=users,
        userisadmin=userisadmin(username))


@get('/admin/remove-user/:username')
@requires_auth
@requires_admin
def removeuser(username):
    if username == currentuser():
        return 'não é possível remover usuário corrente'
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM users
            WHERE username = %s
        ''', (username,))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return redirect('/admin')

@post('/admin/save-new-user')
@requires_auth
@requires_admin
def newuser():
    assert 'username' in request.forms
    username = request.forms.username
    if username.strip() == '':
        return 'usuário inválido'
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    c = getdb().cursor()
    try:
        c.execute('''
            INSERT INTO users (
                username, password, is_admin
            )
            VALUES (%s, %s, %s)
        ''', (username, sha1password, False))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return u'usuário %s criado com senha %s' % ( username, password )


@get('/admin/force-new-password/:username')
@requires_auth
@requires_admin
def forceuserpassword(username):
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    if username == currentuser():
        return 'não é possível forçar nova senha de usuário corrente'
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE users
            SET password = %s
            WHERE username = %s
        ''', (sha1password, username))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return u'usuário %s teve nova senha forçada: %s' % ( username, password )


########################################################################################
# Funções auxiliares
########################################################################################


def validateuserdb(user, passwd):
    passwdsha1 = sha1(passwd).hexdigest()
    c = getdb().cursor()
    c.execute('''
        SELECT username
        FROM users
        WHERE username = %s
            AND password = %s
    ''', (user, passwdsha1))
    r = c.fetchone()
    if not r: return False
    else: return True


def validatesession(session_id):
    c = getdb().cursor()
    c.execute('''
        SELECT session_id
        FROM sessions
        WHERE session_id = %s
    ''', (session_id,))
    r = c.fetchone()
    if r: return True
    else: return False


def currentuser():
    session_id = request.get_cookie('ticket_session')
    c = getdb().cursor()
    c.execute('''
        SELECT username
        FROM sessions
        WHERE session_id = %s
    ''', (session_id,))
    r = c.fetchone()
    return r[0]


def userisadmin(username):
    "Checa se usuário tem poderes administrativos"
    c = getdb().cursor()
    c.execute('''
        SELECT is_admin
        FROM users
        WHERE username = %s
    ''', (username,))
    return c.fetchone()[0]


def removesession(session_id):
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM sessions
            WHERE session_id = %s
        ''', (session_id,))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()


def makesession(user):
    c = getdb().cursor()
    try:
        session_id = str(uuid4())
        c.execute('''
            INSERT INTO sessions (session_id, username)
            VALUES (%s,%s)
        ''', (session_id, user))
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return session_id


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

    bottle.debug(config.devel_mode)
    run(host=config.bind_address, port=config.bind_port,
        server='paste', reloader=config.devel_mode)
