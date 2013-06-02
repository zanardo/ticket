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
import bottle
import getopt
import random
import getopt
import os.path
import sqlite3
import datetime
import mimetypes

from uuid import uuid4
from hashlib import sha1
from bottle import route, request, run, view, response, static_file, \
    redirect, local, get, post

import config

import ticket.db
import ticket.user
import ticket.webadmin
import ticket.weblogin
import ticket.webticket
import ticket.webstatic

VERSION = '1.6dev'