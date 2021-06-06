import mimetypes
import re
import time
import zlib

from bottle import get, post, redirect, request, response, route, view

import ticket
import ticket.auth
from ticket import db
from ticket.config import cfg
from ticket.context import TemplateContext
from ticket.log import log

from .mail import sendmail
from .tickets import (
    sanitizecomment,
    tags_desc,
    ticketblocks,
    ticketdepends,
    tickettags,
    tickettitle,
)


@route("/")
@view("list-tickets")
@ticket.auth.requires_auth
def index():
    """
    Lista tickets utilizando critérios de um filtro.
    """
    # A página padrão exibe os tickets ordenados por prioridade.
    if "filter" not in request.query.keys():
        return redirect("/?filter=o:p")
    filter = request.query.filter
    if filter.strip() == "":
        filter = "o:p"

    # Redireciona ao ticket caso pesquisa seja #NNNNN
    m = re.match(r"^#(\d+)$", filter)
    if m:
        return redirect("/ticket/%s" % m.group(1))

    # Dividindo filtro em tokens separados por espaços
    tokens = filter.strip().split()

    limit = ""
    search = []
    status = "and status = 0"
    order = "order by datemodified desc"
    orderdate = "datemodified"

    # Abrangência dos filtros (status)
    # T: todos
    # F: fechados
    # A: abertos
    if re.match(r"^[TFA] ", filter):
        tr = {"T": "", "A": "and status = 0", "F": "and status = 1"}
        status = tr[tokens[0]]
        tokens.pop(0)  # Removendo primeiro item

    sql = "select * from tickets where ( 1 = 1 ) "
    sqlparams = []

    for t in tokens:

        # Limite de resultados (l:NNN)
        m = re.match(r"^l:(\d+)$", t)
        if m:
            limit = "limit %s " % m.group(1)
            continue

        # Palavra-chave (t:TAG)
        m = re.match(r"^t:(.+)$", t)
        if m:
            sql += "and id in ( select ticket_id from tags where tag  = ? ) "
            sqlparams.append(m.group(1))
            continue

        # Ordenação (o:m)
        m = re.match(r"^o:([mcfpv])$", t)
        if m:
            o = m.group(1)
            if o == "c":
                order = "order by datecreated desc "
                orderdate = "datecreated"
            elif o == "m":
                order = "order by datemodified desc "
                orderdate = "datemodified"
            elif o == "f":
                order = "order by dateclosed desc "
                orderdate = "dateclosed"
            elif o == "v":
                order = "order by datedue asc "
                orderdate = "datedue"
            elif o == "p":
                order = "order by priority asc, datecreated asc "
                orderdate = ""
            continue

        # Usuário de criação, fechamento, modificação (u:USER)
        m = re.match(r"^u:(.+)$", t)
        if m:
            u = m.group(1)
            sql += """
                and ( ( user = ? )
                or ( id in
                    ( select ticket_id from comments where user = ? )
                )
                or ( id in
                    ( select ticket_id from timetrack where user = ? )
                )
                or ( id in
                    ( select ticket_id from statustrack where user = ? ) )
                )
            """
            sqlparams += [u, u, u, u]
            continue

        # Faixa de data de criação, fechamento, modificação e previsão
        m = re.match(
            r"^d([fmcv]):(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$", t
        )
        if m:
            dt = ""
            y1, m1, d1, y2, m2, d2 = m.groups()[1:]
            dt = {
                "c": "datecreated",
                "m": "datemodified",
                "f": "dateclosed",
                "v": "datedue",
            }[m.group(1)]
            sql += (
                "and %s between '%s-%s-%s 00:00:00' " "and '%s-%s-%s 23:59:59' "
            ) % (dt, y1, m1, d1, y2, m2, d2)
            continue

        # Data de criação, fechamento, modificação e previsão
        m = re.match(r"^d([fmc]):(\d{4})(\d{2})(\d{2})$", t)
        if m:
            dt = ""
            y1, m1, d1 = m.groups()[1:]
            dt = {
                "c": "datecreated",
                "m": "datemodified",
                "f": "dateclosed",
                "v": "datedue",
            }[m.group(1)]
            sql += (
                "and %s between '%s-%s-%s 00:00:00' " "and '%s-%s-%s 23:59:59' "
            ) % (dt, y1, m1, d1, y1, m1, d1)
            continue

        # Faixa de prioridade (p:1-2)
        m = re.match(r"^p:([1-5])-([1-5])$", t)
        if m:
            p1, p2 = m.groups()
            sql += "and priority between %s and %s " % (p1, p2)
            continue

        # Prioridade (p:1)
        m = re.match(r"^p:([1-5])$", t)
        if m:
            p1 = m.group(1)
            sql += "and priority = %s " % (p1,)
            continue

        # Restrição de tickets (administrador, normal e todos)
        m = re.match(r"^r:([ant])$", t)
        if m:
            a = {"a": "1", "n": "0", "t": "admin_only"}[m.group(1)]
            sql += "and admin_only = %s " % a
            continue

        # Texto para busca
        search.append(t)

    ctx = TemplateContext()

    # Caso usuário não seja administrador, vamos filtrar os
    # tickets que ele não tem acesso.
    if not ctx.user_is_admin:
        sql += "and admin_only = 0 "

    if len(search) > 0:
        s = " ".join(search)
        sql += "and id in ( select docid from search where search match ? ) "
        sqlparams.append(s)

    # Caso ordenação seja por data de previsão, mostrando
    # somente tickets com date de previsão preenchida.
    if orderdate == "datedue":
        sql += "and datedue is not null "

    # Caso ordenação seja por data de fechamento, mostrando
    # somente os tickets fechados.
    if orderdate == "dateclosed":
        sql += "and status = 1 "

    if status:
        sql += "%s " % status

    if order:
        sql += "%s " % order

    if limit:
        sql += "%s " % limit

    c = db.get_cursor()
    c.execute(sql, sqlparams)
    tickets = []
    for t in c:
        ticketdict = dict(t)
        ticketdict["tags"] = tickettags(t["id"])
        tickets.append(ticketdict)

    ctx.tickets = tickets
    ctx.filter = filter
    ctx.orderdate = orderdate
    ctx.tags_desc = tags_desc()

    return dict(ctx=ctx)


@get("/ticket/new")
@view("ticket-new")
@ticket.auth.requires_auth
def newticket():
    """
    Tela de novo ticket.
    """
    return dict(ctx=TemplateContext())


@post("/ticket/new")
@ticket.auth.requires_auth
def newticketpost():
    """
    Salva um novo ticket.
    """
    assert "title" in request.forms
    title = request.forms.get("title").strip()
    if title == "":
        return "erro: título inválido"
    username = ticket.auth.current_user()
    with db.db_trans() as c:
        c.execute(
            """
            insert into tickets (
                title,
                user
            )
            values (
                :title,
                :username
            )
        """,
            {"title": title, "username": username},
        )
        ticket_id = c.lastrowid
        db.populate_search(ticket_id)
    return redirect("/ticket/%s" % ticket_id)


@get("/ticket/<ticket_id:int>")
@view("ticket")
@ticket.auth.requires_auth
def showticket(ticket_id):
    """
    Exibe detalhes de um ticket.
    """
    c = db.get_cursor()
    # Obtém dados do ticket

    ctx = TemplateContext()

    sql_is_admin = ""
    if not ctx.user_is_admin:
        sql_is_admin = "and admin_only = 0"

    c.execute(
        """
        select *
        from tickets
        where id = :ticket_id
    """
        + sql_is_admin,
        {"ticket_id": ticket_id},
    )
    ctx.ticket = c.fetchone()

    if not ctx.ticket:
        return "ticket inexistente!"

    # Obtém notas, mudanças de status e registro de tempo

    ctx.comments = []

    # Mudanças de status
    c.execute(
        """
        select datecreated,
            user,
            status
        from statustrack
        where ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        reg = dict(r)
        reg["type"] = "statustrack"
        ctx.comments.append(reg)

    # Comentários
    c.execute(
        """
        select datecreated,
            user,
            comment
        from comments
        where ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        reg = dict(r)
        reg["comment"] = sanitizecomment(reg["comment"])
        reg["type"] = "comments"
        ctx.comments.append(reg)

    # Registro de tempo
    c.execute(
        """
        select datecreated,
            user,
            minutes
        from timetrack
        where ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        reg = dict(r)
        reg["type"] = "timetrack"
        ctx.comments.append(reg)

    # Arquivos anexos
    c.execute(
        """
        select datecreated,
            user,
            name,
            id
        from files
        where ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        reg = dict(r)
        reg["type"] = "files"
        ctx.comments.append(reg)

    # Ordenando comentários por data
    ctx.comments = sorted(
        ctx.comments, key=lambda comments: comments["datecreated"]
    )

    # Obtém resumo de tempo trabalhado

    ctx.timetrack = []
    c.execute(
        """
        select user,
            sum(minutes) as minutes
        from timetrack
        where ticket_id = :ticket_id
        group by user
        order by user
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        ctx.timetrack.append(dict(r))

    # Obtém palavras-chave
    ctx.tags = tickettags(ticket_id)

    # Obtém dependências
    ctx.blocks = ticketblocks(ticket_id)
    ctx.depends = ticketdepends(ticket_id)

    ctx.user = ticket.auth.user_ident(ctx.username)

    db.get_db().commit()

    # Renderiza template
    return dict(ctx=ctx)


@get("/ticket/file/<id:int>/:name")
@ticket.auth.requires_auth
def getfile(id, name):
    """
    Retorna um arquivo em anexo.
    """
    mime = mimetypes.guess_type(name)[0]
    if mime is None:
        mime = "application/octet-stream"
    c = db.get_cursor()
    c.execute(
        """
        select files.ticket_id as ticket_id,
            files.size as size,
            files.contents as contents,
            tickets.admin_only as admin_only
        from files
        join tickets
            on tickets.id = files.ticket_id
        where files.id = :id
    """,
        {"id": id},
    )
    row = c.fetchone()
    blob = zlib.decompress(row["contents"])
    if (
        not ticket.auth.user_admin(ticket.auth.current_user())
        and row["admin_only"] == 1
    ):
        return "você não tem permissão para acessar este recurso!"
    else:
        response.content_type = mime
        return blob


@post("/ticket/<ticket_id:int>/close")
@ticket.auth.requires_auth
def closeticket(ticket_id):
    """
    Fecha um ticket.
    """
    # Verifica se existem tickets que bloqueiam este
    # ticket que ainda estão abertos.
    c = db.get_cursor()
    c.execute(
        """
        select d.ticket_id as ticket_id
        from dependencies as d
            inner join tickets as t
                on t.id = d.ticket_id
        where d.blocks = :ticket_id
            and t.status = 0
    """,
        {"ticket_id": ticket_id},
    )
    blocks = [r["ticket_id"] for r in c]
    if blocks:
        return (
            "os seguintes tickets bloqueiam este ticket e "
            + "estão em aberto: %s" % " ".join([str(x) for x in blocks])
        )

    username = ticket.auth.current_user()
    with db.db_trans() as c:
        c.execute(
            """
            update tickets
            set status = 1,
                dateclosed = datetime('now', 'localtime'),
                datemodified = datetime('now', 'localtime')
            where id = :ticket_id
        """,
            {"ticket_id": ticket_id},
        )
        c.execute(
            """
            insert into statustrack (
                ticket_id,
                user,
                status
            )
            values (
                :ticket_id,
                :username,
                'close'
            )
        """,
            {"ticket_id": ticket_id, "username": username},
        )

    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/title")
@ticket.auth.requires_auth
def changetitle(ticket_id):
    """
    Altera título de um ticket.
    """
    assert "text" in request.forms
    title = request.forms.get("text").strip()
    if title == "":
        return "erro: título inválido"
    with db.db_trans() as c:
        c.execute(
            """
            update tickets
            set title = :title
            where id = :ticket_id
        """,
            {"title": title, "ticket_id": ticket_id},
        )
        db.populate_search(ticket_id)
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/datedue")
@ticket.auth.requires_auth
def changedatedue(ticket_id):
    """
    Altera data de previsão de solução de um ticket.
    """
    assert "datedue" in request.forms
    datedue = request.forms.get("datedue").strip()
    if datedue != "":
        # Testando máscara
        if not re.match(r"^2\d{3}-\d{2}-\d{2}$", datedue):
            return "erro: data de previsão inválida"
        # Testando validade da data
        try:
            time.strptime(datedue, "%Y-%m-%d")
        except ValueError:
            return "erro: data de previsão inválida"
        datedue += " 23:59:59"
    else:
        datedue = None
    with db.db_trans() as c:
        c.execute(
            """
            update tickets
            set datedue = :datedue
            where id = :ticket_id
        """,
            {"datedue": datedue, "ticket_id": ticket_id},
        )
    return redirect("/ticket/%s" % ticket_id)


@get("/ticket/<ticket_id:int>/admin-only/:toggle")
@ticket.auth.requires_auth
@ticket.auth.requires_admin
def changeadminonly(ticket_id, toggle):
    """
    Tornar ticket somente visível para administradores.
    """
    assert toggle in ("0", "1")
    with db.db_trans() as c:
        c.execute(
            """
            update tickets
            set admin_only = :toggle
            where id = :ticket_id
        """,
            {"toggle": toggle, "ticket_id": ticket_id},
        )
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/tags")
@ticket.auth.requires_auth
def changetags(ticket_id):
    """
    Altera tags de um ticket.
    """
    assert "text" in request.forms
    tags = list(set(request.forms.get("text").strip().split()))
    with db.db_trans() as c:
        c.execute(
            """
            delete from tags
            where ticket_id = :ticket_id
        """,
            locals(),
        )
        for tag in tags:
            c.execute(
                """
                insert into tags (
                    ticket_id,
                    tag
                )
                values (
                    :ticket_id,
                    :tag
            )""",
                {"ticket_id": ticket_id, "tag": tag},
            )
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/dependencies")
@ticket.auth.requires_auth
def changedependencies(ticket_id):
    """
    Altera dependências de um ticket.
    """
    assert "text" in request.forms
    deps = request.forms.get("text")
    deps = deps.strip().split()
    # Validando dependências
    for dep in deps:
        # Valida sintaxe
        if not re.match(r"^\d+$", dep):
            return "sintaxe inválida para dependência: %s" % dep
        # Valida se não é o mesmo ticket
        dep = int(dep)
        if dep == ticket_id:
            return "ticket não pode bloquear ele mesmo"
        # Valida se ticket existe
        with db.db_trans() as c:
            c.execute("SELECT count(*) FROM tickets WHERE id=:dep", locals())
            if c.fetchone()[0] == 0:
                return "ticket %s não existe" % dep
        # Valida dependência circular
        if ticket_id in ticketblocks(dep):
            return "dependência circular: %s" % dep
    with db.db_trans() as c:
        c.execute(
            """
            delete from dependencies
            where ticket_id = :ticket_id
        """,
            locals(),
        )
        for dep in deps:
            c.execute(
                """
                insert into dependencies (
                    ticket_id,
                    blocks
                )
                values (
                    :ticket_id,
                    :dep
                )
            """,
                {"ticket_id": ticket_id, "dep": dep},
            )
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/minutes")
@ticket.auth.requires_auth
def registerminutes(ticket_id):
    """
    Registra tempo trabalhado em um ticket.
    """
    assert "minutes" in request.forms
    if not re.match(r"^[\-0-9\.]+$", request.forms.get("minutes")):
        return "tempo inválido"
    minutes = float(request.forms.get("minutes"))
    if minutes <= 0.0:
        return "tempo inválido"
    username = ticket.auth.current_user()
    with db.db_trans() as c:
        c.execute(
            """
            insert into timetrack (
                ticket_id,
                user,
                minutes
            )
            values (
                :ticket_id,
                :username,
                :minutes
            )""",
            {"ticket_id": ticket_id, "username": username, "minutes": minutes},
        )
        c.execute(
            """
            update tickets
            set datemodified = datetime('now', 'localtime')
            where id = :ticket_id
        """,
            {"ticket_id": ticket_id},
        )
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/note")
@ticket.auth.requires_auth
def newnote(ticket_id):
    """
    Cria um novo comentário para um ticket.
    """
    assert "text" in request.forms

    contacts = []
    if "contacts" in request.forms:
        contacts = request.forms.get("contacts").strip().split()

    note = request.forms.get("text")
    if note.strip() == "":
        return "nota inválida"

    if len(contacts) > 0:
        note += " [Notificação enviada para: %s]" % (", ".join(contacts))

    username = ticket.auth.current_user()
    with db.db_trans() as c:
        c.execute(
            """
            insert into comments (
                ticket_id,
                user,
                comment
            )
            values (
                :ticket_id,
                :username,
                :note
            )
            """,
            {"ticket_id": ticket_id, "username": username, "note": note},
        )
        c.execute(
            """
            update tickets
            set datemodified = datetime('now', 'localtime')
            where id = :ticket_id
        """,
            {"ticket_id": ticket_id},
        )
        db.populate_search(ticket_id)

    user = ticket.auth.user_ident(username)

    if len(contacts) > 0 and user["name"] and user["email"]:
        title = tickettitle(ticket_id)
        subject = "#%s - %s" % (ticket_id, title)
        body = """
[%s] (%s):

%s


-- Este é um e-mail automático enviado pelo sistema ticket.
        """ % (
            time.strftime("%Y-%m-%d %H:%M"),
            user["name"],
            note,
        )

        sendmail(user["email"], contacts, cfg("smtp", "host"), subject, body)

    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/reopen")
@ticket.auth.requires_auth
def reopenticket(ticket_id):
    """
    Reabre um ticket.
    """
    # Verifica se existem tickets bloqueados por este ticket
    # que estão fechados.
    c = db.get_cursor()
    c.execute(
        """
        select d.blocks as blocks
        from dependencies as d
            inner join tickets as t
                on t.id = d.blocks
        where d.ticket_id = :ticket_id
            and t.status = 1
    """,
        {"ticket_id": ticket_id},
    )
    blocks = [r["blocks"] for r in c]
    if blocks:
        return (
            "os seguintes tickets são bloqueados por este ticket "
            + "e estão fechados: %s" % " ".join([str(x) for x in blocks])
        )
    username = ticket.auth.current_user()
    with db.db_trans() as c:
        c.execute(
            """
            update tickets
            set status = 0,
                dateclosed = null,
                datemodified = datetime('now', 'localtime')
            where id = :ticket_id
        """,
            {"ticket_id": ticket_id},
        )
        c.execute(
            """
            insert into statustrack (
                ticket_id,
                user,
                status
            )
            values (
                :ticket_id,
                :username,
                'reopen'
            )
        """,
            {"ticket_id": ticket_id, "username": username},
        )
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/priority")
@ticket.auth.requires_auth
def changepriority(ticket_id):
    """
    Altera a prioridade de um ticket.
    """
    assert "prio" in request.forms
    assert re.match(r"^[1-5]$", request.forms.get("prio"))
    priority = int(request.forms.get("prio"))
    with db.db_trans() as c:
        c.execute(
            """
            update tickets
            set priority = :priority
            where id = :ticket_id
        """,
            {"priority": priority, "ticket_id": ticket_id},
        )
    return redirect("/ticket/%s" % ticket_id)


@post("/ticket/<ticket_id:int>/upload")
@ticket.auth.requires_auth
def uploadfile(ticket_id):
    """
    Anexa um arquivo ao ticket.
    """
    if "file" not in request.files:
        return "arquivo inválido"
    filename = request.files.get("file").filename
    maxfilesize = int(cfg("attachments", "max-size"))
    blob = b""
    filesize = 0
    while True:
        chunk = request.files.get("file").file.read(4096)
        if not chunk:
            break
        chunksize = len(chunk)
        if filesize + chunksize > maxfilesize:
            return "erro: arquivo maior do que máximo permitido"
        filesize += chunksize
        blob += chunk
    log.debug(type(blob))
    blob = zlib.compress(blob)
    username = ticket.auth.current_user()
    with db.db_trans() as c:
        c.execute(
            """
            insert into files (
                ticket_id,
                name,
                user,
                size,
                contents
            )
            values (
                :ticket_id,
                :filename,
                :username,
                :filesize,
                :blob
            )
        """,
            {
                "ticket_id": ticket_id,
                "filename": filename,
                "username": username,
                "filesize": filesize,
                "blob": blob,
            },
        )
        c.execute(
            """
            update tickets
            set datemodified = datetime('now', 'localtime')
            where id = :ticket_id
        """,
            {"ticket_id": ticket_id},
        )
    return redirect("/ticket/%s" % ticket_id)
