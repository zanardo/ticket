import re

from bottle import route, static_file


@route("/static/:filename")
def static(filename):
    """
    Retorna um arquivo estático em ./static.
    """
    assert re.match(r"^[\w\d\-]+\.[\w\d\-]+$", filename)
    return static_file("static/%s" % filename, root=".")
