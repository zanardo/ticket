# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

from bottle import route, view, get, post, redirect, response, request

import re
import time

import ticket.db
import ticket.user
import ticket.mail

import config

# Listagem de tickets
@route('/')
@view('list-tickets')
@ticket.user.requires_auth
def index():
    # Lista tickets utilizando critérios de um filtro
    # A página padrão exibe os tickets ordenados por prioridade
    if 'filter' not in request.query.keys():
        return redirect('/?filter=o:p g:p')
    filter = request.query.filter
    if filter.strip() == '':
        filter = u'o:p g:p'

    # Redireciona ao ticket caso pesquisa seja #NNNNN
    m = re.match(r'^#(\d+)$', filter)
    if m:
        return redirect('/%s' % m.group(1))

    # Dividindo filtro em tokens separados por espaços
    tokens = filter.strip().split()

    limit = tags = user = date = prio = ''
    search = []
    status = u'and status = 0'
    order = u'order by datemodified desc'
    orderdate = 'datemodified'
    group = ''

    # Abrangência dos filtros (status)
    # T: todos
    # F: fechados
    # A: abertos
    if re.match(r'^[TFA] ', filter):
        tr = { 'T': '', 'A': u'and status = 0', 'F': u'and status = 1' }
        status = tr[tokens[0]]
        tokens.pop(0)   # Removendo primeiro item

    sql = u'select * from tickets where ( 1 = 1 ) '
    sqlparams = []

    for t in tokens:

        # Limite de resultados (l:NNN)
        m = re.match(r'^l:(\d+)$', t)
        if m:
            limit = 'limit %s ' % m.group(1)
            continue

        # Palavra-chave (t:TAG)
        m = re.match(r'^t:(.+)$', t)
        if m:
            sql += u'and id in ( select ticket_id from tags where tag  = ? ) '
            sqlparams.append(m.group(1))
            continue

        # Ordenação (o:m)
        m = re.match(r'^o:([mcfpv])$', t)
        if m:
            o = m.group(1)
            if o == 'c':
                order = u'order by datecreated desc '
                orderdate = 'datecreated'
            elif o == 'm':
                order = u'order by datemodified desc '
                orderdate = 'datemodified'
            elif o == 'f':
                order = u'order by dateclosed desc '
                orderdate = 'dateclosed'
            elif o == 'v':
                order = u'order by datedue asc '
                orderdate = 'datedue'
            elif o == 'p':
                order = u'order by priority asc, datecreated asc '
                orderdate = ''
            continue

        # Agrupamento (g:[dp])
        m = re.match(r'^g:([dp])$', t)
        if m:
            group = { 'p': 'priority', 'd': 'date' }[m.group(1)]
            continue

        # Usuário de criação, fechamento, modificação (u:USER)
        m = re.match(r'^u:(.+)$', t)
        if m:
            u = m.group(1)
            sql += (u"and ( ( user = ? ) "
                "or ( id in ( select ticket_id from comments where user = ? ) ) "
                "or ( id in ( select ticket_id from timetrack where user = ? ) ) "
                "or ( id in ( select ticket_id from statustrack where user = ? ) ) )" )
            sqlparams += [u,u,u,u]
            continue

        # Faixa de data de criação, fechamento, modificação e previsão
        m = re.match(r'^d([fmcv]):(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$',
                     t)
        if m:
            dt = ''
            y1, m1, d1, y2, m2, d2 = m.groups()[1:]
            dt = {'c': 'datecreated', 'm': 'datemodified',
                'f': 'dateclosed', 'v': 'datedue'}[m.group(1)]
            sql += ( u"and %s between '%s-%s-%s 00:00:00' "
                     u"and '%s-%s-%s 23:59:59' " ) % ( dt, y1, m1, d1, y2, m2, d2 )
            continue

        # Data de criação, fechamento, modificação e previsão
        m = re.match(r'^d([fmc]):(\d{4})(\d{2})(\d{2})$', t)
        if m:
            dt = ''
            y1, m1, d1 = m.groups()[1:]
            dt = {'c': 'datecreated', 'm': 'datemodified',
                'f': 'dateclosed', 'v': 'datedue'}[m.group(1)]
            sql += ( u"and %s between '%s-%s-%s 00:00:00' "
                "and '%s-%s-%s 23:59:59' " ) % ( dt, y1, m1, d1, y1, m1, d1 )
            continue

        # Faixa de prioridade (p:1-2)
        m = re.match(r'^p:([1-5])-([1-5])$', t)
        if m:
            p1, p2 = m.groups()
            sql += u"and priority between %s and %s " % (p1, p2)
            continue

        # Prioridade (p:1)
        m = re.match(r'^p:([1-5])$', t)
        if m:
            p1 = m.group(1)
            sql += u"and priority = %s " % (p1,)
            continue

        # Restrição de tickets (administrador, normal e todos)
        m = re.match(r'^r:([ant])$', t)
        if m:
            a = {'a': '1', 'n': '0', 't': 'admin_only'}[m.group(1)]
            sql += u"and admin_only = %s " % a
            continue

        # Texto para busca
        search.append(t)

    # Validando agrupamentos
    if ( orderdate == '' and group == 'date' ) \
                or ( orderdate != '' and group == 'priority' ):
        return 'agrupamento inválido!'

    # Caso usuário não seja administrador, vamos filtrar os
    # tickets que ele não tem acesso.
    username = ticket.user.currentuser()
    user_is_admin = ticket.user.userisadmin(username)
    if not user_is_admin:
        sql += u"and admin_only = 0 "

    searchstr = ''
    if len(search) > 0:
        s = ' '.join(search)
        sql += u"and id in ( select docid from search where search match ? ) "
        sqlparams.append(s)

    # Caso ordenação seja por data de previsão, mostrando
    # somente tickets com date de previsão preenchida.
    if orderdate == 'datedue':
        sql += u'and datedue is not null '

    # Caso ordenação seja por data de fechamento, mostrando
    # somente os tickets fechados.
    if orderdate == 'dateclosed':
        sql += u'and status = 1 '

    if status:
        sql += u"%s " % status

    if order:
        sql += "%s " % order

    if limit:
        sql += "%s " % limit

    c = ticket.db.getcursor()
    c.execute(sql, sqlparams)
    tickets = []
    for t in c:
        ticketdict = dict(t)
        ticketdict['tags'] = tickettags(t['id'])
        tickets.append(ticketdict)

    return dict(tickets=tickets, filter=filter, priodesc=config.priodesc, 
        priocolor=config.priocolor, tagsdesc=tagsdesc(), version=ticket.VERSION,
        username=username, userisadmin=user_is_admin, 
        orderdate=orderdate, weekdays=config.weekdays, group=group)



# Tela de novo ticket
@get('/new-ticket')
@view('new-ticket')
@ticket.user.requires_auth
def newticket():
    # Tela de novo ticket
    username = ticket.user.currentuser()
    return dict(version=ticket.VERSION, username=username,
        userisadmin=ticket.user.userisadmin(username))


# Salva novo ticket
@post('/new-ticket')
@ticket.user.requires_auth
def newticketpost():
    # Salva um novo ticket
    assert 'title' in request.forms
    title = request.forms.title.strip()
    if title == '':
        return 'erro: título inválido'
    username = ticket.user.currentuser()
    with ticket.db.db_trans() as c:
        c.execute("insert into tickets (title, user) "
            "values ( :title, :username )", locals())
        ticket_id = c.lastrowid
        ticket.db.populatesearch(ticket_id)

    return redirect('/%s' % ticket_id)


# Exibe os detalhes de um ticket
@get('/<ticket_id:int>')
@view('show-ticket')
@ticket.user.requires_auth
def showticket(ticket_id):
    # Exibe detalhes de um ticket
    c = ticket.db.getcursor()
    # Obtém dados do ticket

    username = ticket.user.currentuser()
    user_is_admin = ticket.user.userisadmin(username)
    sql_is_admin = ''
    if not user_is_admin:
        sql_is_admin = 'and admin_only = 0'

    c.execute("select * from tickets where id = :ticket_id " + sql_is_admin,
        locals())
    t = c.fetchone()

    if not t:
        return 'ticket inexistente!'

    # Obtém notas, mudanças de status e registro de tempo

    comments = []

    # Mudanças de status
    c.execute("select datecreated, user, status from statustrack "
        "where ticket_id = :ticket_id", locals())
    for r in c:
        reg = dict(r)
        reg['type'] = 'statustrack'
        comments.append(reg)

    # Comentários
    c.execute("select datecreated, user, comment from comments "
        "where ticket_id = :ticket_id", locals())
    for r in c:
        reg = dict(r)
        reg['comment'] = sanitizecomment(reg['comment'])
        reg['type'] = 'comments'
        comments.append(reg)

    # Registro de tempo
    c.execute("select datecreated, user, minutes from timetrack "
        "where ticket_id = :ticket_id", locals())
    for r in c:
        reg = dict(r)
        reg['type'] = 'timetrack'
        comments.append(reg)

    # Arquivos anexos
    c.execute("select datecreated, user, name, id from files "
        "where ticket_id = :ticket_id", locals())
    for r in c:
        reg = dict(r)
        reg['type'] = 'files'
        comments.append(reg)

    # Ordenando comentários por data
    comments = sorted(comments, key=lambda comments: comments['datecreated'])

    # Obtém resumo de tempo trabalhado

    timetrack = []
    c.execute("select user, sum(minutes) as minutes from timetrack "
        "where ticket_id = :ticket_id group by user order by user",
            locals())
    for r in c:
        timetrack.append(dict(r))

    # Obtém palavras-chave
    tags = tickettags(ticket_id)

    # Obtém dependências
    blocks = ticketblocks(ticket_id)
    depends = ticketdepends(ticket_id)

    ticket.db.getdb().commit()

    # Renderiza template

    return dict(ticket=t, comments=comments, priocolor=config.priocolor,
        priodesc=config.priodesc, timetrack=timetrack, tags=tags,
        tagsdesc=tagsdesc(), version=ticket.VERSION, username=username,
        userisadmin=ticket.user.userisadmin(username), user=ticket.user.userident(username),
        blocks=blocks, depends=depends, features=config.features)

@get('/file/<id:int>/:name')
@ticket.user.requires_auth
def getfile(id, name):
    # Retorna um arquivo em anexo
    mime = mimetypes.guess_type(name)[0]
    if mime is None:
        mime = 'application/octet-stream'
    c = ticket.db.getcursor()
    c.execute("select files.ticket_id as ticket_id, files.size as size "
        ", files.contents as contents, tickets.admin_only as admin_only "
        "from files join tickets on tickets.id = files.ticket_id "
        "where files.id = :id", locals())
    row = c.fetchone()
    blob = zlib.decompress(row['contents'])
    if not ticket.user.userisadmin(ticket.user.currentuser()) and row['admin_only'] == 1:
        return 'você não tem permissão para acessar este recurso!'
    else:
        response.content_type = mime
        return blob


@post('/close-ticket/<ticket_id:int>')
@ticket.user.requires_auth
def closeticket(ticket_id):
    # Fecha um ticket
    # Verifica se existem tickets que bloqueiam este
    # ticket que ainda estão abertos.
    c = ticket.db.getcursor()
    c.execute("select d.ticket_id as ticket_id from dependencies as d "
        "inner join tickets as t on t.id = d.ticket_id "
        "where d.blocks = :ticket_id and t.status = 0", locals())
    blocks = [r['ticket_id'] for r in c]
    if blocks:
        return 'os seguintes tickets bloqueiam este ticket e ' + \
               'estão em aberto: %s' % ' '.join([str(x) for x in blocks])

    username = ticket.user.currentuser()
    with ticket.db.db_trans() as c:
        c.execute("update tickets set status = 1, "
            "dateclosed = datetime('now', 'localtime'), "
            "datemodified = datetime('now', 'localtime') "
            "where id = :ticket_id", locals())
        c.execute("insert into statustrack (ticket_id, user, status ) "
            "values (:ticket_id, :username, 'close')", locals())

    return redirect('/%s' % ticket_id)


@post('/change-title/<ticket_id:int>')
@ticket.user.requires_auth
def changetitle(ticket_id):
    # Altera título de um ticket
    assert 'text' in request.forms
    title = request.forms.text.strip()
    if title == '':
        return 'erro: título inválido'
    with ticket.db.db_trans() as c:
        c.execute("update tickets set title = :title where id = :ticket_id",
            locals())
        ticket.db.populatesearch(ticket_id)
    return redirect('/%s' % ticket_id)


@post('/change-datedue/<ticket_id:int>')
@ticket.user.requires_auth
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
    with ticket.db.db_trans() as c:
        c.execute("update tickets set datedue = :datedue "
            "where id = :ticket_id", locals())
    return redirect('/%s' % ticket_id)


@get('/change-admin-only/<ticket_id:int>/:toggle')
@ticket.user.requires_auth
@ticket.user.requires_admin
def changeadminonly(ticket_id, toggle):
    # Tornar ticket somente visível para administradores
    assert toggle in ( '0', '1' )
    with ticket.db.db_trans() as c:
        c.execute("update tickets set admin_only = :toggle "
            "where id = :ticket_id", locals())
    return redirect('/%s' % ticket_id)


@post('/change-tags/<ticket_id:int>')
@ticket.user.requires_auth
def changetags(ticket_id):
    # Altera tags de um ticket
    assert 'text' in request.forms
    tags = list(set(request.forms.text.strip().split()))
    with ticket.db.db_trans() as c:
        c.execute("delete from tags where ticket_id = :ticket_id", locals())
        for tag in tags:
            c.execute("insert into tags ( ticket_id, tag ) "
                "values ( :ticket_id, :tag )", locals())
    return redirect('/%s' % ticket_id)


@post('/change-dependencies/<ticket_id:int>')
@ticket.user.requires_auth
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
        with ticket.db.db_trans() as c:
            c.execute('SELECT count(*) FROM tickets WHERE id=:dep', locals())
            if c.fetchone()[0] == 0:
                return u'ticket %s não existe' % dep
        # Valida dependência circular
        if ticket_id in ticketblocks(dep):
            return u'dependência circular: %s' % dep
    with ticket.db.db_trans() as c:
        c.execute("delete from dependencies where ticket_id = :ticket_id",
            locals())
        for dep in deps:
            c.execute("insert into dependencies ( ticket_id, blocks ) "
                "values ( :ticket_id, :dep )", locals())
    return redirect('/%s' % ticket_id)


@post('/register-minutes/<ticket_id:int>')
@ticket.user.requires_auth
def registerminutes(ticket_id):
    # Registra tempo trabalhado em um ticket
    assert 'minutes' in request.forms
    if not re.match(r'^[\-0-9\.]+$', request.forms.minutes):
        return 'tempo inválido'
    minutes = float(request.forms.minutes)
    if minutes <= 0.0:
        return 'tempo inválido'
    username = ticket.user.currentuser()
    with ticket.db.db_trans() as c:
        c.execute("insert into timetrack (ticket_id, user, minutes ) "
            "values ( :ticket_id, :username, :minutes )", locals())
        c.execute("update tickets "
            "set datemodified = datetime('now', 'localtime') "
            "where id = :ticket_id", locals())
    return redirect('/%s' % ticket_id)


@post('/new-note/<ticket_id:int>')
@ticket.user.requires_auth
def newnote(ticket_id):
    # Cria um novo comentário para um ticket
    assert 'text' in request.forms

    contacts = []
    if 'contacts' in request.forms:
        contacts = request.forms.contacts.strip().split()

    note = request.forms.text
    if note.strip() == '':
        return 'nota inválida'

    if len(contacts) > 0:
        note += u' [Notificação enviada para: %s]' % (
            ', '.join(contacts)
        )

    username = ticket.user.currentuser()
    with ticket.db.db_trans() as c:
        c.execute("insert into comments ( ticket_id, user, comment ) "
            "values ( :ticket_id, :username, :note )", locals())
        c.execute("update tickets "
            "set datemodified = datetime('now', 'localtime') "
            "where id = :ticket_id", locals())
        ticket.db.populatesearch(ticket_id)

    user = ticket.user.userident(username)

    if len(contacts) > 0 and user['name'] and user['email']:
        title = tickettitle(ticket_id)
        subject = u'#%s - %s' % (ticket_id, title)
        body = u'''
[%s] (%s):

%s


-- Este é um e-mail automático enviado pelo sistema ticket.
        ''' % ( time.strftime('%Y-%m-%d %H:%M'), user['name'], note )

        ticket.mail.sendmail(user['email'], contacts,
            config.mailsmtp, subject, body)

    return redirect('/%s' % ticket_id)


@post('/reopen-ticket/<ticket_id:int>')
@ticket.user.requires_auth
def reopenticket(ticket_id):
    # Reabre um ticket
    # Verifica se existem tickets bloqueados por este ticket
    # que estão fechados.
    c = ticket.db.getcursor()
    c.execute("select d.blocks as blocks from dependencies as d "
        "inner join tickets as t on t.id = d.blocks "
        "where d.ticket_id = :ticket_id and t.status = 1", locals())
    blocks = [r['blocks'] for r in c]
    if blocks:
        return 'os seguintes tickets são bloqueados por este ticket ' + \
               'e estão fechados: %s' % ' '.join([str(x) for x in blocks])
    username = ticket.user.currentuser()
    with ticket.db.db_trans() as c:
        c.execute("update tickets set status = 0, dateclosed = null, "
            "datemodified = datetime('now', 'localtime') "
            "where id = :ticket_id", locals())
        c.execute("insert into statustrack (ticket_id, user, status ) "
            "values (:ticket_id, :username, 'reopen')", locals())
    return redirect('/%s' % ticket_id)


@post('/change-priority/<ticket_id:int>')
@ticket.user.requires_auth
def changepriority(ticket_id):
    # Altera a prioridade de um ticket
    assert 'prio' in request.forms
    assert re.match(r'^[1-5]$', request.forms.prio)
    priority = int(request.forms.prio)
    with ticket.db.db_trans() as c:
        c.execute("update tickets set priority = :priority "
            "where id = :ticket_id", locals())
    return redirect('/%s' % ticket_id)


@post('/upload-file/<ticket_id:int>')
@ticket.user.requires_auth
def uploadfile(ticket_id):
    # Anexa um arquivo ao ticket
    if not 'file' in request.files:
        return 'arquivo inválido'
    filename = request.files.file.filename.decode('utf-8')
    maxfilesize = config.filemaxsize
    blob = ''
    filesize = 0
    while True:
        chunk = request.files.file.file.read(4096)
        if not chunk:
            break
        chunksize = len(chunk)
        if filesize + chunksize > maxfilesize:
            return 'erro: arquivo maior do que máximo permitido'
        filesize += chunksize
        blob += chunk
    blob = buffer(zlib.compress(blob))
    username = ticket.user.currentuser()
    with ticket.db.db_trans() as c:
        c.execute("insert into files ( ticket_id, name, user, size, contents ) "
            "values ( :ticket_id, :filename, :username, :filesize, :blob ) ",
                locals())
        c.execute("update tickets "
            "set datemodified = datetime('now', 'localtime') "
            "where id = :ticket_id", locals())
    return redirect('/%s' % ticket_id)

def tagsdesc():
    # Retorna as descrições de tags
    tagdesc = {}
    c = ticket.db.getcursor()
    c.execute("select tag, description, bgcolor, fgcolor from tagsdesc")
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
    c = ticket.db.getcursor()
    c.execute("select d.blocks, t.title, t.status, t.admin_only "
        "from dependencies as d inner join tickets as t on t.id = d.blocks "
        "where d.ticket_id = :ticket_id", locals())
    for r in c:
        deps[r[0]] = { 'title': r[1], 'status': r[2], 'admin_only': r[3] }
    return deps

def ticketdepends(ticket_id):
    # Retorna quais ticket dependem de um ticket
    deps = {}
    c = ticket.db.getcursor()
    c.execute("select d.ticket_id, t.title, t.status, t.admin_only "
        "from dependencies as d inner join tickets as t on t.id = d.ticket_id "
        "where d.blocks = :ticket_id", locals())
    for r in c:
        deps[r[0]] = { 'title': r[1], 'status': r[2], 'admin_only': r[3] }
    return deps

def tickettags(ticket_id):
    # Retorna tags de um ticket
    c = ticket.db.getcursor()
    c.execute("select tag from tags where ticket_id = :ticket_id", locals())
    return [r['tag'] for r in c]


def tickettitle(ticket_id):
    # Retorna o título de um ticket
    c = ticket.db.getcursor()
    c.execute("select title from tickets where id = :ticket_id", locals())
    return c.fetchone()['title']


def sanitizecomment(comment):
    # Sanitiza o texto do comentário (quebras de linhas, links, etc)
    subs = [ (r'\r', ''), (r'&', '&amp;'), (r'<', '&lt;'), (r'>', '&gt;'),
             (r'\r?\n', '<br>\r\n'), (r'\t', '&nbsp;&nbsp;&nbsp;'),
             (r'  ', '&nbsp;&nbsp;'), (r'#(\d+)', r'<a href="/\1">#\1</a>') ]
    for f, t in subs:
        comment = re.sub(f, t, comment)
    return comment
