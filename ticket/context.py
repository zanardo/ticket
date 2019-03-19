from ticket import __version__
from ticket.user import current_user, user_admin
from ticket.config import cfg, features, priodesc, priocolor
from ticket.tickets import tags_desc


class TemplateContext(object):
    """
    Objeto para simplificar passagem de dados para templates.
    """

    def __init__(self):
        self.version = __version__
        self.username = current_user()
        if self.username is not None:
            self.user_is_admin = user_admin(self.username)
        else:
            self.user_is_admin = 0
        self.config = cfg
        self.features = features
        self.priocolor = priocolor
        self.priodesc = priodesc
        self.tags_desc = tags_desc()
