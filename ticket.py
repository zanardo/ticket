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
import zlib
import time
import paste
import bottle
import getopt
import random
import getopt
import smtplib
import os.path
import sqlite3
import datetime
import mimetypes

from uuid import uuid4
from hashlib import sha1
from functools import wraps
from email.mime.text import MIMEText
from contextlib import contextmanager
from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

VERSION = '1.5dev'

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
    # Retorna um handle de conexão de banco de dados por thread
    if not hasattr(local, 'db'):
        local.db = sqlite3.connect(dbname, detect_types=sqlite3.PARSE_DECLTYPES)
        local.db.row_factory = sqlite3.Row
    return local.db

def getcursor():
    # Retorna um cursor
    return getdb().cursor()

@contextmanager
def db_trans():
    # Abre uma transação no banco de dados e faz o commit ao
    # finalizar o contexto, ou rollback caso algo falhe.
    dbh = getdb()
    c = dbh.cursor()
    try:
        yield c     # Retornar cursor
    except:
        dbh.rollback()
        raise
    finally:
        dbh.commit()

def requires_auth(f):
    # Decorator em router do Bottle para forçar autenticação do usuário
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie(cookie_session_name())
        if not session_id or not validatesession(session_id):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def requires_admin(f):
    # Decorator em router do Bottle para forçar usuário administrador
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.get_cookie(cookie_session_name())
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
    # Lista tickets utilizando critérios de um filtro
    # A página padrão exibe os tickets ordenados por prioridade
    if 'filter' not in request.query.keys():
        return redirect('/?filter=o:p g:p')
    filter = request.query.filter
    if filter.strip() == '': filter = u'o:p g:p'

    # Redireciona ao ticket caso pesquisa seja #NNNNN
    m = re.match(r'^#(\d+)$', filter)
    if m: return redirect('/%s' % m.group(1))

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
        m = re.match(r'^o:([mcfpv])$', t)
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
            elif o == 'v':
                order = u'ORDER BY datedue ASC'
                orderdate = 'datedue'
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

        # Faixa de data de criação, fechamento, modificação e previsão
        m = re.match(r'^d([fmcv]):(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1, m1, d1, y2, m2, d2 = m.groups()[1:]
            if m.group(1) == 'c': dt = 'datecreated'
            elif m.group(1) == 'm': dt = 'datemodified'
            elif m.group(1) == 'f': dt = 'dateclosed'
            elif m.group(1) == 'v': dt = 'datedue'
            sql += u"""
                AND %s BETWEEN '%s-%s-%s 00:00:00' AND '%s-%s-%s 23:59:59'
            """ % ( dt, y1, m1, d1, y2, m2, d2 )
            continue

        # Data de criação, fechamento, modificação e previsão
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1, m1, d1 = m.groups()[1:]
            if m.group(1) == 'c': dt = 'datecreated'
            elif m.group(1) == 'm': dt = 'datemodified'
            elif m.group(1) == 'f': dt = 'dateclosed'
            elif m.group(1) == 'v': dt = 'datedue'
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

        # Restrição de tickets (administrador, normal e todos)
        m = re.match(r'^r:([ant])$', t)
        if m:
            r = m.group(1)
            if r == 'a':
                sql += u"""
                    AND admin_only = 1
                """
            elif r == 'n':
                sql += u"""
                    AND admin_only = 0
                """
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

    # Caso ordenação seja por data de previsão, mostrando
    # somente tickets com date de previsão preenchida.
    if orderdate == 'datedue':
        sql += '''
            AND datedue IS NOT NULL
        '''

    # Caso ordenação seja por data de fechamento, mostrando
    # somente os tickets fechados.
    if orderdate == 'dateclosed':
        sql += '''
            AND status = 1
        '''

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

    c = getcursor()
    c.execute(sql, sqlparams)
    tickets = []
    for ticket in c:
        ticketdict = dict(ticket)
        ticketdict['tags'] = tickettags(ticket['id'])
        tickets.append(ticketdict)

    return dict(tickets=tickets, filter=filter, priodesc=priodesc, 
        priocolor=priocolor, tagsdesc=tagsdesc(), version=VERSION,
        username=username, userisadmin=user_is_admin, 
        orderdate=orderdate, weekdays=weekdays, group=group)


# Tela de login
@get('/login')
@view('login')
def login():
    # Retorna tela de login
    return dict(version=VERSION)


# Valida login
@post('/login')
def validatelogin():
    # Valida login do usuário
    assert 'user' in request.forms
    assert 'passwd' in request.forms
    user = request.forms.user
    passwd = request.forms.passwd
    v = validateuserdb(user, passwd)
    if not v: return 'usuário ou senha inválidos'
    else:
        session_id = makesession(user)
        response.set_cookie(cookie_session_name(), session_id)
        return redirect('/')


@get('/logout')
def logout():
    # Logout do usuário - remove sessão ativa
    session_id = request.get_cookie(cookie_session_name())
    if session_id:
        removesession(session_id)
        response.delete_cookie(cookie_session_name())
        expire_old_sessions()
    return redirect('/login')


# Tela de novo ticket
@get('/new-ticket')
@view('new-ticket')
@requires_auth
def newticket():
    # Tela de novo ticket
    username = currentuser()
    return dict(version=VERSION, username=username,
        userisadmin=userisadmin(username))


# Salva novo ticket
@post('/new-ticket')
@requires_auth
def newticketpost():
    # Salva um novo ticket
    assert 'title' in request.forms
    title = request.forms.title.strip()
    if title == '': return 'erro: título inválido'
    username = currentuser()
    with db_trans() as c:
        c.execute('''
            INSERT INTO TICKETS (
                title, "user"
            )
            VALUES ( :title, :username )
        ''', locals())
        ticket_id = c.lastrowid
        populatesearch(ticket_id)

    return redirect('/%s' % ticket_id)


# Exibe os detalhes de um ticket
@get('/<ticket_id:int>')
@view('show-ticket')
@requires_auth
def showticket(ticket_id):
    # Exibe detalhes de um ticket
    c = getcursor()
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

    # Mudanças de status
    c.execute('''
        SELECT datecreated, user, status
        FROM statustrack
        WHERE ticket_id = :ticket_id
    ''', locals())
    for r in c:
        reg = dict(r)
        reg['type'] = 'statustrack'
        comments.append(reg)

    # Comentários
    c.execute('''
        SELECT datecreated, user, comment
        FROM comments
        WHERE ticket_id = :ticket_id        
    ''', locals())
    for r in c:
        reg = dict(r)
        reg['comment'] = sanitizecomment(reg['comment'])
        reg['type'] = 'comments'
        comments.append(reg)

    # Registro de tempo
    c.execute('''
        SELECT datecreated, user, minutes
        FROM timetrack
        WHERE ticket_id = :ticket_id 
    ''', locals())
    for r in c:
        reg = dict(r)
        reg['type'] = 'timetrack'
        comments.append(reg)

    # Arquivos anexos
    c.execute('''
        SELECT datecreated, user, name, id
        FROM files
        WHERE ticket_id = :ticket_id 
    ''', locals())
    for r in c:
        reg = dict(r)
        reg['type'] = 'files'
        comments.append(reg)

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

    # Obtém dependências
    blocks = ticketblocks(ticket_id)
    depends = ticketdepends(ticket_id)

    getdb().commit()

    # Renderiza template

    return dict(ticket=ticket, comments=comments, priocolor=priocolor,
        priodesc=priodesc, timetrack=timetrack, tags=tags,
        tagsdesc=tagsdesc(), version=VERSION, username=username,
        userisadmin=userisadmin(username), user=userident(username),
        blocks=blocks, depends=depends)

@get('/file/<id:int>/:name')
@requires_auth
def getfile(id, name):
    # Retorna um arquivo em anexo
    mime = mimetypes.guess_type(name)[0]
    if mime is None:
        mime = 'application/octet-stream'
    c = getcursor()
    c.execute('''
        SELECT files.ticket_id AS ticket_id
            , files.size AS size
            , files.contents AS contents
            , tickets.admin_only AS admin_only
        FROM files
            JOIN tickets ON tickets.id = files.ticket_id
        WHERE files.id = :id
    ''', locals())
    row = c.fetchone()
    blob = zlib.decompress(row['contents'])
    if not userisadmin(currentuser()) and row['admin_only'] == 1:
        return 'você não tem permissão para acessar este recurso!'
    else:
        response.content_type = mime
        return blob


@post('/close-ticket/<ticket_id:int>')
@requires_auth
def closeticket(ticket_id):
    # Fecha um ticket
    # Verifica se existem tickets que bloqueiam este
    # ticket que ainda estão abertos.
    c = getcursor()
    c.execute('''
        SELECT d.ticket_id
        FROM dependencies AS d
        INNER JOIN tickets AS t ON t.id = d.ticket_id
        WHERE d.blocks = :ticket_id
          AND t.status = 0
    ''', locals())
    blocks = []
    for r in c:
        blocks.append(r[0])
    if len(blocks) > 0:
        return 'os seguintes tickets bloqueiam este ticket e estão em aberto: %s' % \
            ' '.join([str(x) for x in blocks])

    username = currentuser()
    with db_trans() as c:
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

    return redirect('/%s' % ticket_id)


@post('/change-title/<ticket_id:int>')
@requires_auth
def changetitle(ticket_id):
    # Altera título de um ticket
    assert 'text' in request.forms
    title = request.forms.text.strip()
    if title == '': return 'erro: título inválido'
    with db_trans() as c:
        c.execute('''
            UPDATE tickets
            SET title = :title
            WHERE id = :ticket_id
        ''', locals())
        populatesearch(ticket_id)
    return redirect('/%s' % ticket_id)


@post('/change-datedue/<ticket_id:int>')
@requires_auth
def changedatedue(ticket_id):
    # Altera data de previsão de solução de um ticket
    assert 'datedue' in request.forms
    datedue = request.forms.datedue.strip()
    if datedue != '':
        # Testando máscara
        if not re.match(r'^2\d{3}-\d{2}-\d{2}$', datedue):
            return 'erro: data de previsão inválida'
        # Testando validade da data
        try:
            time.strptime(datedue, '%Y-%m-%d')
        except ValueError:
            return 'erro: data de previsão inválida'
        datedue += ' 23:59:59'
    else:
        datedue = None
    with db_trans() as c:
        c.execute('''
            UPDATE tickets
            SET datedue = :datedue
            WHERE id = :ticket_id
        ''', locals())
    return redirect('/%s' % ticket_id)


@get('/change-admin-only/<ticket_id:int>/:toggle')
@requires_auth
@requires_admin
def changeadminonly(ticket_id, toggle):
    # Tornar ticket somente visível para administradores
    assert toggle in ( '0', '1' )
    with db_trans() as c:
        c.execute('''
            UPDATE tickets
            SET admin_only = :toggle
            WHERE id = :ticket_id
        ''', locals())
    return redirect('/%s' % ticket_id)


@post('/change-tags/<ticket_id:int>')
@requires_auth
def changetags(ticket_id):
    # Altera tags de um ticket
    assert 'text' in request.forms
    tags = list(set(request.forms.text.strip().split()))
    with db_trans() as c:
        c.execute('''
            DELETE FROM tags
            WHERE ticket_id = :ticket_id
        ''', locals())
        for tag in tags:
            c.execute('''
                INSERT INTO tags ( ticket_id, tag )
                VALUES ( :ticket_id, :tag )
            ''', locals())
    return redirect('/%s' % ticket_id)


@post('/change-dependencies/<ticket_id:int>')
@requires_auth
def changedependencies(ticket_id):
    # Altera dependências de um ticket
    assert 'text' in request.forms
    deps = request.forms.text
    deps = deps.strip().split()
    # Validando dependências
    for dep in deps:
        # Valida sintaxe
        if not re.match(r'^\d+$', dep):
            return u'sintaxe inválida para dependência: %s' % dep
        # Valida se não é o mesmo ticket
        dep = int(dep)
        if dep == ticket_id:
            return u'ticket não pode bloquear ele mesmo'
        # Valida se ticket existe
        with db_trans() as c:
            c.execute('''SELECT count(*) FROM tickets WHERE id=:dep''', locals())
            if c.fetchone()[0] == 0:
                return u'ticket %s não existe' % dep
        # Valida dependência circular
        if ticket_id in ticketblocks(dep):
            return u'dependência circular: %s' % dep
    with db_trans() as c:
        c.execute('''
            DELETE FROM dependencies
            WHERE ticket_id = :ticket_id
        ''', locals())
        for dep in deps:
            c.execute('''
                INSERT INTO dependencies ( ticket_id, blocks )
                VALUES ( :ticket_id, :dep )
            ''', locals())
    return redirect('/%s' % ticket_id)


@post('/register-minutes/<ticket_id:int>')
@requires_auth
def registerminutes(ticket_id):
    # Registra tempo trabalhado em um ticket
    assert 'minutes' in request.forms
    if not re.match(r'^[\-0-9\.]+$', request.forms.minutes):
        return 'tempo inválido'
    minutes = float(request.forms.minutes)
    if minutes <= 0.0: return 'tempo inválido'
    username = currentuser()
    with db_trans() as c:
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
    return redirect('/%s' % ticket_id)


@post('/new-note/<ticket_id:int>')
@requires_auth
def newnote(ticket_id):
    # Cria um novo comentário para um ticket
    assert 'text' in request.forms
    assert 'contacts' in request.forms
    note = request.forms.text
    contacts = request.forms.contacts.strip().split()
    if note.strip() == '': return 'nota inválida'

    if len(contacts) > 0:
        note += u' [Notificação enviada para: %s]' % (
            ', '.join(contacts)
        )

    username = currentuser()
    with db_trans() as c:
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

    user = userident(username)

    if len(contacts) > 0 and user['name'] and user['email']:
        title = tickettitle(ticket_id)
        subject = u'#%s - %s' % (ticket_id, title)
        body = u'''
[%s] (%s):

%s


-- Este é um e-mail automático enviado pelo sistema ticket.
        ''' % ( time.strftime('%Y-%m-%d %H:%M'), user['name'], note )

        sendmail(user['email'], contacts,
            getconfig('mail.smtp'), subject, body)

    return redirect('/%s' % ticket_id)


@post('/reopen-ticket/<ticket_id:int>')
@requires_auth
def reopenticket(ticket_id):
    # Reabre um ticket
    # Verifica se existem tickets bloqueados por este ticket
    # que estão fechados.
    c = getcursor()
    c.execute('''
        SELECT d.blocks
        FROM dependencies AS d
        INNER JOIN tickets AS t ON t.id = d.blocks
        WHERE d.ticket_id = :ticket_id
          AND t.status = 1
    ''', locals())
    blocks = []
    for r in c:
        blocks.append(r[0])
    if len(blocks) > 0:
        return 'os seguintes tickets são bloqueados por este ticket e estão fechados: %s' % \
            ' '.join([str(x) for x in blocks])
    username = currentuser()
    with db_trans() as c:
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
    return redirect('/%s' % ticket_id)


@post('/change-priority/<ticket_id:int>')
@requires_auth
def changepriority(ticket_id):
    # Altera a prioridade de um ticket
    assert 'prio' in request.forms
    assert re.match(r'^[1-5]$', request.forms.prio)
    priority = int(request.forms.prio)
    with db_trans() as c:
        c.execute('''
            UPDATE tickets
            SET priority = :priority
            WHERE id = :ticket_id
        ''', locals())
    return redirect('/%s' % ticket_id)


@post('/upload-file/<ticket_id:int>')
@requires_auth
def uploadfile(ticket_id):
    # Anexa um arquivo ao ticket
    if not 'file' in request.files:
        return 'arquivo inválido'
    filename = request.files.file.filename.decode('utf-8')
    maxfilesize = int(getconfig('file.maxsize'))
    blob = ''
    filesize = 0
    while True:
        chunk = request.files.file.file.read(4096)
        if not chunk: break
        chunksize = len(chunk)
        if filesize + chunksize > maxfilesize:
            return 'erro: arquivo maior do que máximo permitido'
        filesize += chunksize
        blob += chunk
    blob = buffer(zlib.compress(blob))
    username = currentuser()
    with db_trans() as c:
        c.execute('''
            INSERT INTO files ( ticket_id, name, user, size, contents )
            VALUES ( :ticket_id, :filename, :username, :filesize, :blob )
        ''', locals())
        c.execute('''
            UPDATE tickets
            SET datemodified = datetime('now', 'localtime')
            WHERE id = :ticket_id
        ''', locals())
    return redirect('/%s' % ticket_id)


@route('/static/:filename')
def static(filename):
    # Retorna um arquivo estático em ./static
    assert re.match(r'^[\w\d\-]+\.[\w\d\-]+$', filename)
    return static_file('static/%s' % filename, root='.')


@get('/change-password')
@requires_auth
@view('change-password')
def changepassword():
    # Tela de alteração de senha do usuário
    username = currentuser()
    return dict(username=username, version=VERSION,
        userisadmin=userisadmin(username))


@post('/change-password')
@requires_auth
def changepasswordsave():
    # Altera a senha do usuário
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
    with db_trans() as c:
        c.execute('''
            UPDATE users
            SET password = :passwdsha1
            WHERE username = :username
        ''', locals())
    return redirect('/')


@get('/admin')
@view('admin')
@requires_auth
@requires_admin
def admin():
    # Tela de administração
    username = currentuser()
    users = []
    c = getcursor()
    c.execute('''
        SELECT username, is_admin, name, email
        FROM users
        ORDER BY username
    ''')
    for user in c:
        user = dict(user)
        user['name'] = user['name'] or ''
        user['email'] = user['email'] or ''
        users.append(user)
    config = {}
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
    # Salva configurações
    config = {}
    for k in request.forms:
        if k in ('mail.smtp', 'file.maxsize'):
            config[k] = getattr(request.forms, k)
    with db_trans() as c:
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
    return redirect('/admin')


@get('/admin/remove-user/:username')
@requires_auth
@requires_admin
def removeuser(username):
    # Apaga um usuário
    if username == currentuser():
        return 'não é possível remover usuário corrente'
    with db_trans() as c:
        c.execute('''
            DELETE FROM users
            WHERE username = :username
        ''', locals())
    return redirect('/admin')


@get('/admin/edit-user/:username')
@view('edit-user')
@requires_auth
@requires_admin
def edituser(username):
    # Exibe tela de edição de usuários
    c = getcursor()
    c.execute('''
        SELECT name, email
        FROM users
        WHERE username = :username
    ''', locals())
    r = c.fetchone()
    name = ''
    email = ''
    if not r:
        return 'usuário %s não encontrado!' % username
    else:
        name = r['name'] or ''
        email = r['email'] or ''
        return dict(user=username, name=name, email=email, username=currentuser(),
            version=VERSION, userisadmin=userisadmin(currentuser()))


@post('/admin/edit-user/:username')
@requires_auth
@requires_admin
def editusersave(username):
    # Salva os dados de um usuário editado
    assert 'name' in request.forms
    assert 'email' in request.forms
    name = request.forms.name.strip()
    email = request.forms.email.strip()
    with db_trans() as c:
        c.execute('''
            UPDATE users
            SET name=:name, email=:email
            WHERE username=:username
        ''', locals())
    return redirect('/admin')


@post('/admin/save-new-user')
@requires_auth
@requires_admin
def newuser():
    # Cria um novo usuário
    assert 'username' in request.forms
    username = request.forms.username
    if username.strip() == '':
        return 'usuário inválido'
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    with db_trans() as c:
        c.execute('''
            INSERT INTO users (
                username, password, is_admin
            )
            VALUES (:username, :sha1password, 0)
        ''', locals())
    return u'usuário %s criado com senha %s' % ( username, password )


@get('/admin/force-new-password/:username')
@requires_auth
@requires_admin
def forceuserpassword(username):
    # Reseta senha de um usuário
    password = str(int(random.random() * 999999))
    sha1password = sha1(password).hexdigest()
    if username == currentuser():
        return 'não é possível forçar nova senha de usuário corrente'
    with db_trans() as c:
        c.execute('''
            UPDATE users
            SET password = :sha1password
            WHERE username = :username
        ''', locals())
    return u'usuário %s teve nova senha forçada: %s' % ( username, password )


@get('/admin/change-user-admin-status/:username/:status')
@requires_auth
@requires_admin
def changeuseradminstatus(username, status):
    # Altera status de administrador de um usuário
    if username == currentuser():
        return 'não é possível alterar status de admin para usuário corrente'
    assert status in ( '0', '1' )
    with db_trans() as c:
        c.execute('''
            UPDATE users
            SET is_admin = :status
            WHERE username = :username
        ''', locals())
    return redirect('/admin')


@get('/admin/reindex-fts')
@requires_auth
@requires_admin
def reindexfts():
    # Recria o índice de Full Text Search
    with db_trans() as c:
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
    return 'índices de full text search recriados!'


########################################################################################
# Funções auxiliares
########################################################################################


def validateuserdb(user, passwd):
    # Valida usuário e senha no banco de dados
    passwdsha1 = sha1(passwd).hexdigest()
    c = getcursor()
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
    # Valida sessão ativa no banco de dados
    c = getcursor()
    c.execute('''
        SELECT session_id
        FROM sessions
        WHERE session_id = :session_id
    ''', locals())
    r = c.fetchone()
    if r: return True
    else: return False


def userident(username):
    # Retorna nome e e-mail de usuário
    c = getcursor()
    c.execute('''
        SELECT name, email
        FROM users
        WHERE username=:username
    ''', locals())
    r = c.fetchone()
    return dict(r)


def currentuser():
    # Retorna usuário corrente
    session_id = request.get_cookie(cookie_session_name())
    c = getcursor()
    c.execute('''
        SELECT username
        FROM sessions
        WHERE session_id = :session_id
    ''', locals())
    r = c.fetchone()
    return r[0]


def userisadmin(username):
    # Checa se usuário tem poderes administrativos
    c = getcursor()
    c.execute('''
        SELECT is_admin
        FROM users
        WHERE username = :username
    ''', locals())
    r = c.fetchone()
    return r[0]


def removesession(session_id):
    # Remove uma sessão do banco de dados
    with db_trans() as c:
        c.execute('''
            DELETE FROM sessions
            WHERE session_id = :session_id
        ''', locals())


def makesession(user):
    # Cria uma nova sessão no banco de dados
    with db_trans() as c:
        session_id = str(uuid4())
        c.execute('''
            INSERT INTO sessions (session_id, username)
            VALUES (:session_id, :user)
        ''', locals())
    return session_id


def tagsdesc():
    # Retorna as descrições de tags
    tagdesc = {}
    c = getcursor()
    c.execute('''
        SELECT tag, description, bgcolor, fgcolor
        FROM tagsdesc
    ''')
    for r in c:
        tagdesc[r['tag']] = {
            'description': r['description'] or '',
            'bgcolor': r['bgcolor'] or '#00D6D6',
            'fgcolor': r['fgcolor'] or '#4D4D4D'
        }
    return tagdesc

def ticketblocks(ticket_id):
    # Retorna quais ticket são bloqueados por um ticket
    deps = {}
    c = getcursor()
    c.execute('''
        SELECT d.blocks, t.title, t.status, t.admin_only
        FROM dependencies AS d
        INNER JOIN tickets AS t ON t.id = d.blocks
        WHERE d.ticket_id = :ticket_id
    ''', locals())
    for r in c:
        deps[r[0]] = { 'title': r[1], 'status': r[2], 'admin_only': r[3] }
    return deps

def ticketdepends(ticket_id):
    # Retorna quais ticket dependem de um ticket
    deps = {}
    c = getcursor()
    c.execute('''
        SELECT d.ticket_id, t.title, t.status, t.admin_only
        FROM dependencies AS d
        INNER JOIN tickets AS t ON t.id = d.ticket_id
        WHERE d.blocks = :ticket_id
    ''', locals())
    for r in c:
        deps[r[0]] = { 'title': r[1], 'status': r[2], 'admin_only': r[3] }
    return deps

def tickettags(ticket_id):
    # Retorna tags de um ticket
    tags = []
    c = getcursor()
    c.execute('''
        SELECT tag
        FROM tags
        WHERE ticket_id = :ticket_id
    ''', locals())
    for r in c:
        tags.append(r[0])
    return tags


def tickettitle(ticket_id):
    # Retorna o título de um ticket
    c = getcursor()
    c.execute('''
        SELECT title
        FROM tickets
        WHERE id = :ticket_id
    ''', locals())
    title = c.fetchone()[0]
    return title


def getconfig(key):
    # Retorna o valor de uma configuração
    c = getcursor()
    c.execute('''
        SELECT value
        FROM config
        WHERE key = :key
    ''', locals())
    r = c.fetchone()
    return r[0]


def sendmail(fromemail, toemail, smtpserver, subject, body):
    # Envia um e-mail
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
    # Sanitiza o texto do comentário (quebras de linhas, links, etc)
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
    # Popula o índice de busca full-text para um ticket
    text = ''
    c = getcursor()     # Utiliza transação do caller
    text += ' ' + tickettitle(ticket_id) + ' '
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
    # Cria o banco de dados caso arquivo não exista
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
    # Expira sessões mais antigas que 7 dias
    with db_trans() as c:
        c.execute('''
            DELETE FROM sessions
            WHERE julianday('now') - julianday(date_login) > 7
        ''')


def cookie_session_name():
    # Retorna o nome do cookie para a sessão
    return 'ticket_session_%s' % port


########################################################################################
# Main
########################################################################################


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
