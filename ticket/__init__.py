# -*- coding: utf-8 -*-
#
# Copyright (c) J. A. Zanardo Jr. <zanardo@gmail.com>
#
# https://github.com/zanardo/ticket
#
# Para detalhes do licenciamento, ver COPYING na distribuição
#

import config

import ticket.db
import ticket.user
import ticket.webadmin
import ticket.weblogin
import ticket.webticket
import ticket.webstatic

VERSION = '1.6.1'

class TemplateContext(object):
    """ Objeto para simplificar passagem de dados para templates """
    def __init__(self):
        self.version = VERSION
        self.config = config
        self.username = ticket.user.currentuser()
        if self.username is not None:
            self.user_is_admin = ticket.user.userisadmin(self.username)
        else:
            self.user_is_admin = 0
        self.features = config.features
        self.tagsdesc = ticket.tickets.tagsdesc()
