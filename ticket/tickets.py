import re
from typing import Dict, List

from ticket.db import get_cursor


def tags_desc() -> Dict[str, Dict[str, str]]:
    """
    Retorna as descrições de tags.
    """
    tagdesc = {}
    c = get_cursor()
    c.execute(
        """
        select tag,
            description,
            bgcolor,
            fgcolor
        from tagsdesc
    """
    )
    for r in c:
        tagdesc[r["tag"]] = {
            "description": r["description"] or "",
            "bgcolor": r["bgcolor"] or "#00D6D6",
            "fgcolor": r["fgcolor"] or "#4D4D4D",
        }
    return tagdesc


def ticket_blocks(ticket_id) -> Dict[str, Dict[str, str]]:
    """
    Retorna quais ticket são bloqueados por um ticket.
    """
    deps = {}
    c = get_cursor()
    c.execute(
        """
        select d.blocks,
            t.title,
            t.status,
            t.admin_only
        from dependencies as d
            inner join tickets as t
                on t.id = d.blocks
        where d.ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        deps[r[0]] = {"title": r[1], "status": r[2], "admin_only": r[3]}
    return deps


def ticket_depends(ticket_id) -> Dict[str, Dict[str, str]]:
    """
    Retorna quais ticket dependem de um ticket.
    """
    deps = {}
    c = get_cursor()
    c.execute(
        """
        select d.ticket_id,
            t.title,
            t.status,
            t.admin_only
        from dependencies as d
            inner join tickets as t
                on t.id = d.ticket_id
        where d.blocks = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    for r in c:
        deps[r[0]] = {"title": r[1], "status": r[2], "admin_only": r[3]}
    return deps


def ticket_tags(ticket_id) -> List[str]:
    """
    Retorna tags de um ticket.
    """
    c = get_cursor()
    c.execute(
        """
        select tag
        from tags
        where ticket_id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    return [r["tag"] for r in c]


def ticket_title(ticket_id) -> str:
    """
    Retorna o título de um ticket.
    """
    c = get_cursor()
    c.execute(
        """
        select title
        from tickets
        where id = :ticket_id
    """,
        {"ticket_id": ticket_id},
    )
    return c.fetchone()["title"]


def sanitize_comment(comment) -> str:
    """
    Sanitiza o texto do comentário (quebras de linhas, links, etc).
    """
    subs = [
        (r"\r", ""),
        (r"&", "&amp;"),
        (r"<", "&lt;"),
        (r">", "&gt;"),
        (r"\r?\n", "<br>\r\n"),
        (r"\t", "&nbsp;&nbsp;&nbsp;"),
        (r"  ", "&nbsp;&nbsp;"),
        (r"#(\d+)", r"<a href='/ticket/\1'>#\1</a>"),
    ]
    for f, t in subs:
        comment = re.sub(f, t, comment)
    return comment
