#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

try:
    import bottle
except ImportError:
    print 'ERRO: o seguinte módulo do Python precisa ser instalado: bottle'
    exit(1)

try:
    import paste
except ImportError:
    print 'ERRO: o seguinte módulo do Python precisa ser instalado: paste'
    exit(1)

import re
import os
import sys
import time
import getopt
import random
import getopt
import smtplib
import os.path
import sqlite3
import datetime

from uuid import uuid4
from hashlib import sha1
from functools import wraps
from email.mime.text import MIMEText
from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

VERSION = '1.3dev'

# Cores de fundo das prioridades
priocolor = {
    1: '#FF8D8F',
    2: '#99CC00',
    3: '#FF9966',
    4: '#6DF2B2',
    5: '#9FEFF2',
}

# Descrição das prioridades
priodesc = {
    1: 'Ação Urgente',
    2: 'Atenção',
    3: 'Prioridade Normal',
    4: 'Baixa Prioridade',
    5: 'Baixíssima Prioridade',
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
    '''Retorna um handle de conexão de banco de dados por thread'''
    if not hasattr(local, 'db'):
        local.db = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES)
        local.db.row_factory = sqlite3.Row
    return local.db

def requires_auth(f):
    '''Decorator em router do Bottle para forçar autenticação do usuário'''
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie('ticket_session')
        if not session_id or not validatesession(session_id):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def requires_admin(f):
    '''Decorator em router do Bottle para forçar usuário administrador'''
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
    '''Lista tickets utilizando critérios de um filtro'''
    # A página padrão exibe os tickets ordenados por prioridade
    if 'filter' not in request.query.keys():
        return redirect('/?filter=o:p g:p')
    filter = request.query.filter
    if filter.strip() == '': filter = u'o:p g:p'

    # Redireciona ao ticket caso pesquisa seja #NNNNN
    m = re.match(r'^#(\d+)$', filter)
    if m: return redirect('/%s' % m.group(1))

    c = getdb().cursor()

    # Dividindo filtro em tokens separados por espaços
    tokens = filter.strip().split()

    limit = tags = user = date = prio = ''
    search = []
    status = u'AND status = 0'
    order = u'ORDER BY datemodified DESC'
    orderdate = 'datemodified'
    group = ''

    # Abrangência dos filtros (status)
    # T: todos
    # F: fechados
    # A: abertos
    if re.match(r'^[TFA] ', filter):
        if tokens[0] == 'T': status = ''
        elif tokens[0] == 'A': status = u'AND status = 0'
        elif tokens[0] == 'F': status = u'AND status = 1'
        tokens.pop(0)   # Removendo primeiro item

    sql = u'''
        SELECT *
        FROM tickets
        WHERE ( 1 = 1 )
    '''
    sqlparams = []

    for t in tokens:

        # Limite de resultados (l:NNN)
        m = re.match(r'^l:(\d+)$', t)
        if m:
            limit = 'LIMIT %s' % m.group(1)
            continue

        # Palavra-chave (t:TAG)
        m = re.match(r'^t:(.+)$', t)
        if m:
            sql += u'''
                AND id IN ( SELECT ticket_id FROM tags WHERE tag  = ? )
            '''
            sqlparams.append(m.group(1))
            continue

        # Ordenação (o:m)
        m = re.match(r'^o:([mcfp])$', t)
        if m:
            o = m.group(1)
            if o == 'c':
                order = u'ORDER BY datecreated DESC'
                orderdate = 'datecreated'
            elif o == 'm':
                order = u'ORDER BY datemodified DESC'
                orderdate = 'datemodified'
            elif o == 'f':
                order = u'ORDER BY dateclosed DESC'
                orderdate = 'dateclosed'
            elif o == 'p':
                order = u'ORDER BY priority ASC, datecreated ASC'
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
            sql += u"""
               AND ( ( user = ? )
                OR ( id IN ( SELECT ticket_id FROM comments WHERE user = ? ) )
                OR ( id IN ( SELECT ticket_id FROM timetrack WHERE user = ? ) )
                OR ( id IN ( SELECT ticket_id FROM statustrack WHERE user = ? ) ) )
            """
            sqlparams += [u,u,u,u]
            continue

        # Faixa de data de criação, fechamento, modificação
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1, m1, d1, y2, m2, d2 = m.groups()[1:]
            if m.group(1) == 'c': dt = 'datecreated'
            elif m.group(1) == 'm': dt = 'datemodified'
            elif m.group(1) == 'f': dt = 'dateclosed'
            sql += u"""
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
            sql += u"""
                AND %s BETWEEN '%s-%s-%s 00:00:00' AND '%s-%s-%s 23:59:59'
            """ % ( dt, y1, m1, d1, y1, m1, d1 )
            continue

        # Faixa de prioridade (p:1-2)
        m = re.match(r'^p:([1-5])-([1-5])$', t)
        if m:
            p1, p2 = m.groups()
            sql += u"""
                AND priority BETWEEN %s AND %s
            """ % (p1, p2)
            continue

        # Prioridade (p:1)
        m = re.match(r'^p:([1-5])$', t)
        if m:
            p1 = m.group(1)
            sql += u"""
                AND priority = %s
            """ % (p1,)
            continue

        # Texto para busca
        search.append(t)

    # Validando agrupamentos
    if ( orderdate == '' and group == 'date' ) \
                or ( orderdate != '' and group == 'priority' ):
        return 'agrupamento inválido!'

    # Caso usuário não seja administrador, vamos filtrar os
    # tickets que ele não tem acesso.
    username = currentuser()
    user_is_admin = userisadmin(username)
    if not user_is_admin:
        sql += u"""
            AND admin_only = 0
        """

    searchstr = ''
    if len(search) > 0:
        s = ' '.join(search)
        sql += u"""
            AND id IN ( SELECT docid FROM search WHERE search MATCH ? )
        """
        sqlparams.append(s)

    if status != '':
        sql += '''
            %s
        ''' % status

    if order != '':
        sql += '''
            %s
        ''' % order

    if limit != '':
        sql += '''
            %s
        ''' % limit

    c.execute(sql, sqlparams)
    tickets = []
    for ticket in c:
        ticketdict = dict(ticket)
        ticketdict['tags'] = tickettags(ticket['id'])
        tickets.append(ticketdict)

    getdb().commit()

    return dict(tickets=tickets, filter=filter, priodesc=priodesc, 
        priocolor=priocolor, tagsdesc=tagsdesc(), version=VERSION,
        username=username, userisadmin=user_is_admin, 
        orderdate=orderdate, weekdays=weekdays, group=group)


# Tela de login
@get('/login')
@view('login')
def login():
    '''Retorna tela de login'''
    return dict(version=VERSION)


# Valida login
@post('/login')
def validatelogin():
    '''Valida login do usuário'''
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
    '''Logout do usuário - remove sessão ativa'''
    session_id = request.get_cookie('ticket_session')
    if session_id:
        removesession(session_id)
        response.delete_cookie('ticket_session')
        expire_old_sessions()
    return redirect('/login')


# Tela de novo ticket
@get('/new-ticket')
@view('new-ticket')
@requires_auth
def newticket():
    '''Tela de novo ticket'''
    username = currentuser()
    return dict(version=VERSION, username=username,
        userisadmin=userisadmin(username))


# Salva novo ticket
@post('/new-ticket')
@requires_auth
def newticketpost():
    '''Salva um novo ticket'''
    assert 'title' in request.forms
    title = request.forms.title.strip()
    if title == '': return 'erro: título inválido'
    c = getdb().cursor()
    username = currentuser()
    try:
        c.execute('''
            INSERT INTO TICKETS (
                title, "user"
            )
            VALUES ( :title, :username )
        ''', locals())
        ticket_id = c.lastrowid
        populatesearch(ticket_id)
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
    '''Exibe detalhes de um ticket'''
    c = getdb().cursor()

    # Obtém dados do ticket

    username = currentuser()
    user_is_admin = userisadmin(username)
    sql_is_admin = ''
    if not user_is_admin:
        sql_is_admin = '''
            AND admin_only = 0
        '''

    c.execute('''
        SELECT *
        FROM tickets
        WHERE id = :ticket_id
    ''' + sql_is_admin, locals())
    ticket = c.fetchone()

    if not ticket:
        return 'ticket inexistente!'

    # Obtém notas, mudanças de status e registro de tempo

    comments = []

    c.execute('''
        SELECT datecreated
            , user
            , CASE status WHEN \'close\' THEN \'fechado\' WHEN \'reopen\' THEN \'reaberto\' END AS comment
            , 1 AS negrito
            , 0 AS minutes
      FROM statustrack
      WHERE ticket_id = :ticket_id
    ''', locals())
    for r in c:
        comments.append(dict(r))
    c.execute('''
          SELECT datecreated
            , user
            , comment
            , 0 AS negrito
            , 0 AS minutes
          FROM comments
          WHERE ticket_id = :ticket_id        
    ''', locals())
    for r in c:
        cs = dict(r)
        cs['comment'] = sanitizecomment(cs['comment'])
        comments.append(cs)
    c.execute('''
          SELECT datecreated
            , user
            , minutes || \' minutos trabalhados\' AS comment
            , 1 AS negrito
            , minutes
          FROM timetrack
          WHERE ticket_id = :ticket_id 
    ''', locals())
    for r in c:
        comments.append(dict(r))

    # Ordenando comentários por data
    comments = sorted(comments, key=lambda comments: comments['datecreated'])

    # Obtém resumo de tempo trabalhado

    timetrack = []
    c.execute('''
        SELECT user, SUM(minutes) AS minutes
        FROM timetrack
        WHERE ticket_id = :ticket_id
        GROUP BY user
        ORDER BY user
    ''', locals())
    for r in c:
        timetrack.append(dict(r))

    # Obtém palavras-chave
    tags = tickettags(ticket_id)

    # Obtém contatos
    contacts = ticketcontacts(ticket_id)

    getdb().commit()

    # Renderiza template

    return dict(ticket=ticket, comments=comments, priocolor=priocolor,
        priodesc=priodesc, timetrack=timetrack, tags=tags, contacts=contacts,
        tagsdesc=tagsdesc(), version=VERSION, username=username,
        userisadmin=userisadmin(username))


@post('/close-ticket/<ticket_id:int>')
@requires_auth
def closeticket(ticket_id):
    '''Fecha um ticket'''
    c = getdb().cursor()
    username = currentuser()
    try:
        c.execute('''
            UPDATE tickets
            SET status = 1,
                dateclosed = datetime('now', 'localtime'),
                datemodified = datetime('now', 'localtime')
            WHERE id = :ticket_id
        ''', locals())
        c.execute('''
            INSERT INTO statustrack (
                ticket_id, user, status
            )
            VALUES (
                :ticket_id, :username, 'close')
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/change-title/<ticket_id:int>')
@requires_auth
def changetitle(ticket_id):
    '''Alter título de um ticket'''
    assert 'text' in request.forms
    title = request.forms.text.strip()
    if title == '': return 'erro: título inválido'
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE tickets
            SET title = :title
            WHERE id = :ticket_id
        ''', locals())
        populatesearch(ticket_id)
    except:
        getdb().rollback()
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/change-datedue/<ticket_id:int>')
@requires_auth
def changedatedue(ticket_id):
    '''Altera data de previsão de solução de um ticket'''
    assert 'datedue' in request.forms
    datedue = request.forms.datedue.strip()
    if datedue != '' and not re.match(r'^\d{4}-\d{2}-\d{2}$', datedue):
        return 'erro: data de previsão inválida'
    if datedue == '':
        datedue = None
    else: 
        datedue += ' 23:59:59'
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE tickets
            SET datedue = :datedue
            WHERE id = :ticket_id
        ''', locals())
    except:
        getdb().rollback()
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@get('/change-admin-only/<ticket_id:int>/:toggle')
@requires_auth
@requires_admin
def changeadminonly(ticket_id, toggle):
    '''Tornar ticket somente visível para administradores'''
    assert toggle in ( '0', '1' )
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE tickets
            SET admin_only = :toggle
            WHERE id = :ticket_id
        ''', locals())
    except:
        getdb().rollback()
    else:
        getdb().commit()
    return redirect('/%s' % ticket_id)


@post('/change-tags/<ticket_id:int>')
@requires_auth
def changetags(ticket_id):
    '''Altera tags de um ticket'''
    assert 'text' in request.forms
    tags = request.forms.text
    tags = tags.strip().split()
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM tags
            WHERE ticket_id = :ticket_id
        ''', locals())
        for tag in tags:
            c.execute('''
                INSERT INTO tags ( ticket_id, tag )
                VALUES ( :ticket_id, :tag )
            ''', locals())
    except:
        getdb().rollback()
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/change-contacts/<ticket_id:int>')
@requires_auth
def changecontacts(ticket_id):
    '''Altera contatos de um ticket'''
    assert 'contacts' in request.forms
    contacts = request.forms.contacts
    contacts = contacts.strip().split()
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM contacts
            WHERE ticket_id = :ticket_id
        ''', locals())
        for contact in contacts:
            c.execute('''
                INSERT INTO contacts ( ticket_id, email )
                VALUES ( :ticket_id, :contact )
            ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/register-minutes/<ticket_id:int>')
@requires_auth
def registerminutes(ticket_id):
    '''Registra tempo trabalhado em um ticket'''
    assert 'minutes' in request.forms
    if not re.match(r'^[\-0-9\.]+$', request.forms.minutes):
        return 'tempo inválido'
    minutes = float(request.forms.minutes)
    if minutes <= 0.0: return 'tempo inválido'
    c = getdb().cursor()
    username = currentuser()
    try:
        c.execute('''
            INSERT INTO timetrack (
                ticket_id, "user", minutes )
            VALUES ( :ticket_id, :username, :minutes )
        ''', locals())
        c.execute('''
            UPDATE tickets
            SET datemodified = datetime('now', 'localtime')
            WHERE id = :ticket_id
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/new-note/<ticket_id:int>')
@requires_auth
def newnote(ticket_id):
    '''Cria um novo comentário para um ticket'''
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
    username = currentuser()
    try:
        c.execute('''
            INSERT INTO comments (
                ticket_id, "user", comment )
            VALUES ( :ticket_id, :username, :note )
        ''', locals())
        c.execute('''
            UPDATE tickets
            SET datemodified = datetime('now', 'localtime')
            WHERE id = :ticket_id
        ''', locals())
        populatesearch(ticket_id)
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

        sendmail(getconfig('mail.from'), toemail, getconfig('mail.smtp'),
            subject, body)

    return redirect('/%s' % ticket_id)


@post('/reopen-ticket/<ticket_id:int>')
@requires_auth
def reopenticket(ticket_id):
    '''Reabre um ticket'''
    c = getdb().cursor()
    username = currentuser()
    try:
        c.execute('''
            UPDATE tickets
            SET status = 0,
                dateclosed = NULL,
                datemodified = datetime('now', 'localtime')
            WHERE id = :ticket_id
        ''', locals())
        c.execute('''
            INSERT INTO statustrack (
                ticket_id, user, status
            )
            VALUES (
                :ticket_id, :username, 'reopen')
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@post('/change-priority/<ticket_id:int>')
@requires_auth
def changepriority(ticket_id):
    '''Altera a prioridade de um ticket'''
    assert 'prio' in request.forms
    assert re.match(r'^[1-5]$', request.forms.prio)
    priority = int(request.forms.prio)
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE tickets
            SET priority = :priority
            WHERE id = :ticket_id
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()

    return redirect('/%s' % ticket_id)


@route('/static/:filename')
def static(filename):
    '''Retorna um arquivo estático em ./static/'''
    assert re.match(r'^[\w\d\-]+\.[\w\d\-]+$', filename)
    return static_file('static/%s' % filename, root='.')


@get('/change-password')
@requires_auth
@view('change-password')
def changepassword():
    '''Tela de alteração de senha do usuário'''
    username = currentuser()
    return dict(username=username, version=VERSION,
        userisadmin=userisadmin(username))


@post('/change-password')
@requires_auth
def changepasswordsave():
    '''Altera a senha do usuário'''
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
            SET password = :passwdsha1
            WHERE username = :username
        ''', locals())
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
    '''Tela de administração'''
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
    config = {}
    c = getdb().cursor()
    c.execute('''
        SELECT key, value
        FROM config
    ''')
    for k in c:
        config[k[0]] = k[1]
    return dict(version=VERSION, username=username, users=users, config=config,
        userisadmin=userisadmin(username))


@post('/admin/save-config')
@requires_auth
@requires_admin
def saveconfig():
    '''Salva configurações'''
    config = {}
    for k in request.forms:
        if k in ('mail.from', 'mail.smtp'):
            config[k] = getattr(request.forms, k)
    c = getdb().cursor()
    try:
        for conf in config:
            k, v = conf, config[conf]
            c.execute('''
                DELETE FROM config
                WHERE key = :k
            ''', (conf,))
            c.execute('''
                INSERT INTO config
                VALUES (:k, :v)
            ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return redirect('/admin')


@get('/admin/remove-user/:username')
@requires_auth
@requires_admin
def removeuser(username):
    '''Apaga um usuário'''
    if username == currentuser():
        return 'não é possível remover usuário corrente'
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM users
            WHERE username = :username
        ''', locals())
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
    '''Cria um novo usuário'''
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
            VALUES (:username, :sha1password, 0)
        ''', locals())
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
    '''Reseta senha de um usuário'''
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    if username == currentuser():
        return 'não é possível forçar nova senha de usuário corrente'
    c = getdb().cursor()
    try:
        c.execute('''
            UPDATE users
            SET password = :sha1password
            WHERE username = :username
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return u'usuário %s teve nova senha forçada: %s' % ( username, password )


@get('/admin/change-user-admin-status/:username/:status')
@requires_auth
@requires_admin
def changeuseradminstatus(username, status):
    '''Altera status de administrador de um usuário'''
    if username == currentuser():
        return 'não é possível alterar status de admin para usuário corrente'
    c = getdb().cursor()
    assert status in ( '0', '1' )
    try:
        c.execute('''
            UPDATE users
            SET is_admin = :status
            WHERE username = :username
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return redirect('/admin')


@get('/admin/reindex-fts')
@requires_auth
@requires_admin
def reindexfts():
    '''Recria o índice de Full Text Search'''
    c = getdb().cursor()
    try:
        print 'limpando índices'
        c.execute('''
            DELETE FROM search
        ''')
        print 'iniciando recriação dos índices'
        c.execute('''
            SELECT id
            FROM tickets
            ORDER BY id
        ''')
        for r in c:
            print 'reindexando ticket #%s' % r['id']
            populatesearch(r['id'])
    except:
        getdb().rollback()
        raise
    finally:
        getdb().commit()
        return 'índices de full text search recriados!'


########################################################################################
# Funções auxiliares
########################################################################################


def validateuserdb(user, passwd):
    '''Valida usuário e senha no banco de dados'''
    passwdsha1 = sha1(passwd).hexdigest()
    c = getdb().cursor()
    c.execute('''
        SELECT username
        FROM users
        WHERE username = :user
            AND password = :passwdsha1
    ''', locals())
    r = c.fetchone()
    if not r: return False
    else: return True


def validatesession(session_id):
    '''Valida sessão ativa no banco de dados'''
    c = getdb().cursor()
    c.execute('''
        SELECT session_id
        FROM sessions
        WHERE session_id = :session_id
    ''', locals())
    r = c.fetchone()
    if r: return True
    else: return False


def currentuser():
    '''Retorna usuário corrente'''
    session_id = request.get_cookie('ticket_session')
    c = getdb().cursor()
    c.execute('''
        SELECT username
        FROM sessions
        WHERE session_id = :session_id
    ''', locals())
    r = c.fetchone()
    return r[0]


def userisadmin(username):
    '''Checa se usuário tem poderes administrativos'''
    c = getdb().cursor()
    c.execute('''
        SELECT is_admin
        FROM users
        WHERE username = :username
    ''', locals())
    return c.fetchone()[0]


def removesession(session_id):
    '''Remove uma sessão do banco de dados'''
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM sessions
            WHERE session_id = :session_id
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()


def makesession(user):
    '''Cria uma nova sessão no banco de dados'''
    c = getdb().cursor()
    try:
        session_id = str(uuid4())
        c.execute('''
            INSERT INTO sessions (session_id, username)
            VALUES (:session_id, :user)
        ''', locals())
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()
        return session_id


def tagsdesc():
    '''Retorna as descrições de tags'''
    c = getdb().cursor()
    c.execute('''
        SELECT tag, description, bgcolor, fgcolor
        FROM tagsdesc
    ''')
    tagdesc = {}
    for r in c:
        tagdesc[r['tag']] = {
            'description': r['description'] or '',
            'bgcolor': r['bgcolor'] or '#00D6D6',
            'fgcolor': r['fgcolor'] or '#4D4D4D'
        }
    return tagdesc


def tickettags(ticket_id):
    '''Retorna tags de um ticket'''
    tags = []
    c = getdb().cursor()
    c.execute('''
        SELECT tag
        FROM tags
        WHERE ticket_id = :ticket_id
    ''', locals())
    for r in c:
        tags.append(r[0])
    return tags


def ticketcontacts(ticket_id):
    '''Retorna os contatos de um ticket'''
    contacts = []
    c = getdb().cursor()
    c.execute('''
        SELECT email
        FROM contacts
        WHERE ticket_id = :ticket_id
    ''', locals())
    for r in c:
        contacts.append(r[0])
    return contacts


def tickettitle(ticket_id):
    '''Retorna o título de um ticket'''
    c = getdb().cursor()
    c.execute('''
        SELECT title
        FROM tickets
        WHERE id = :ticket_id
    ''', locals())
    title = c.fetchone()[0]
    return title


def getconfig(key):
    '''Retorna o valor de uma configuração'''
    c = getdb().cursor()
    c.execute('''
        SELECT value
        FROM config
        WHERE key = :key
    ''', locals())
    return c.fetchone()[0]


def sendmail(fromemail, toemail, smtpserver, subject, body):
    '''Envia um e-mail'''
    for contact in toemail:
        msg = MIMEText(body.encode('utf-8'))
        msg.set_charset('utf-8')
        msg['Subject'] = subject
        msg['From'] = fromemail
        msg['To'] = contact
        s = smtplib.SMTP(smtpserver, timeout=10)
        s.sendmail(fromemail, contact, msg.as_string())
        s.quit()


def sanitizecomment(comment):
    '''Sanitiza o texto do comentário (quebras de linhas, links, etc)'''
    comment = re.sub(r'\r', '', comment)
    comment = re.sub(r'&', '&amp;', comment)
    comment = re.sub(r'<', '&lt;', comment)
    comment = re.sub(r'>', '&gt;', comment)
    comment = re.sub(r'\r?\n', '<br>\r\n', comment)
    comment = re.sub(r'\t', '&nbsp;&nbsp;&nbsp;', comment)
    comment = re.sub(r'  ', '&nbsp;&nbsp;', comment)
    comment = re.sub(r'#(\d+)', r'<a href="/\1">#\1</a>', comment)
    return comment


def populatesearch(ticket_id):
    '''Popula o índice de busca full-text para um ticket'''
    text = ''
    c = getdb().cursor()
    c.execute('''
        SELECT title
        FROM tickets
        WHERE id = :ticket_id
    ''', locals())
    r = c.fetchone()
    text += ' ' + r['title'] + ' '
    c.execute('''
        SELECT comment
        FROM comments
        WHERE ticket_id = :ticket_id
    ''', locals())
    for r in c:
        text += ' ' + r['comment'] + ' '
    c.execute('''
        DELETE FROM search
        WHERE docid = :ticket_id
    ''', locals())
    c.execute('''
        INSERT INTO search ( docid, text )
        VALUES ( :ticket_id, :text )
    ''', locals())


def createdb(dbname):
    '''Cria o banco de dados caso arquivo não exista'''
    print ';; criando banco de dados %s' % dbname
    db = sqlite3.connect(dbname)
    fp = file('schema.sql', 'r')
    sql = "\n".join(fp.readlines())
    fp.close()
    c = db.cursor()
    c.executescript(sql)
    print ';; banco de dados vazio criado com sucesso!'
    print ';; o primeiro login deverá ser feito com:'
    print ';; usuario: admin     senha: admin'
    db.commit()
    db.close()


def expire_old_sessions():
    '''Expira sessões mais antigas que 7 dias'''
    c = getdb().cursor()
    try:
        c.execute('''
            DELETE FROM sessions
            WHERE julianday('now') - julianday(date_login) > 7
        ''')
    except:
        getdb().rollback()
        raise
    else:
        getdb().commit()


if __name__ == '__main__':

    def usage():
        print '''
            uso: %s -h <host> -p <port> -f <db> [ -d ]
            exemplo: %s -h localhost -p 5000 -f /var/ticket/ticket.db
        ''' % ( sys.argv[0], sys.argv[0] )
        exit(0)

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h:p:f:d')
    except getopt.GetoptError, err:
        usage()

    host = '127.0.0.1'
    port = 5000
    debug = False
    dbname = 'ticket.db'

    for o, a in opts:
        if o == '-d': debug = True
        elif o == '-h': host = a
        elif o == '-p': port = a
        elif o == '-f': dbname = a
        else: usage()

    print ';; carregando ticket'
    print ';; banco de dados = %s' % dbname
    print ';; host = %s' % host
    print ';; port = %s' % port
    if debug:
        print ';; modo de debug ativado'

    # Cria banco de dados caso arquivo não exista
    if not os.path.isfile(dbname):
        createdb(dbname)

    bottle.debug(debug)
    run(host=host, port=port,
        server='paste', reloader=debug)
