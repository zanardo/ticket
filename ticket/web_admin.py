import random

from bottle import get, post, redirect, request, view

from ticket.admin import (
    all_users,
    recreate_fts,
    user,
    user_new,
    user_password_save,
    user_remove,
    user_save,
)
from ticket.auth import current_user, requires_admin, requires_auth
from ticket.context import TemplateContext
from ticket.models import User


@get("/admin")
@view("admin")
@requires_auth
@requires_admin
def admin():
    """
    Tela de administração.
    """
    ctx = TemplateContext()
    ctx.users = all_users()
    return dict(ctx=ctx)


@get("/admin/remove-user/:username")
@requires_auth
@requires_admin
def removeuser(username):
    """
    Apaga um usuário.
    """
    if username == current_user():
        return "não é possível remover usuário corrente"
    user_remove(username)
    return redirect("/admin")


@get("/admin/edit-user/:username")
@view("edit-user")
@requires_auth
@requires_admin
def edituser(username):
    """
    Exibe tela de edição de usuários.
    """
    ctx = TemplateContext()
    user_data = user(username)
    ctx.user = username
    ctx.name = user_data.name or ""
    ctx.email = user_data.email or ""
    return dict(ctx=ctx)


@post("/admin/edit-user/:username")
@requires_auth
@requires_admin
def editusersave(username):
    """
    Salva os dados de um usuário editado.
    """
    assert "name" in request.forms
    assert "email" in request.forms
    user_data = user(username)
    user_data.name = request.forms.get("name").strip()
    user_data.email = request.forms.get("email").strip()
    user_save(user_data)
    return redirect("/admin")


@post("/admin/save-new-user")
@requires_auth
@requires_admin
def newuser():
    """
    Cria um novo usuário.
    """
    assert "username" in request.forms
    username = request.forms.get("username")
    if username.strip() == "":
        return "usuário inválido"
    user_data = User(username=username, is_admin=False, name=None, email=None)
    password = str(int(random.random() * 999999))
    user_new(
        user=user_data,
        password=password,
    )
    return "usuário %s criado com senha %s" % (username, password)


@get("/admin/force-new-password/:username")
@requires_auth
@requires_admin
def forceuserpassword(username):
    """
    Reseta senha de um usuário.
    """
    password = str(int(random.random() * 999999))
    if username == current_user():
        return "não é possível forçar nova senha de usuário corrente"
    user_password_save(username, password)
    return "usuário %s teve nova senha forçada: %s" % (username, password)


@get("/admin/change-user-admin-status/:username/:status")
@requires_auth
@requires_admin
def changeuseradminstatus(username, status):
    """
    Altera status de administrador de um usuário.
    """
    if username == current_user():
        return "não é possível alterar status de admin para usuário corrente"
    assert status in ("0", "1")
    if status == "1":
        admin = True
    else:
        admin = False
    user_data = user(username)
    user_data.is_admin = admin
    user_save(user_data)
    return redirect("/admin")


@get("/admin/reindex-fts")
@requires_auth
@requires_admin
def reindexfts():
    """
    Recria o índice de Full Text Search.
    """
    recreate_fts()
    return "índices de full text search recriados!"
