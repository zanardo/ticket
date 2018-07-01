from ticket import __version__
from ticket.user import (
    currentuser,
    userisadmin
)
from ticket.config import config
from ticket.tickets import tagsdesc


class TemplateContext(object):
    """
    Objeto para simplificar passagem de dados para templates.
    """
    def __init__(self):
        self.version = __version__
        self.username = currentuser()
        if self.username is not None:
            self.user_is_admin = userisadmin(self.username)
        else:
            self.user_is_admin = 0
        self.config = config
        self.tagsdesc = tagsdesc()
