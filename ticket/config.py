import os
import sys
from configparser import ConfigParser

from ticket.log import log

CONFIG_PATH = os.environ.get("TICKET_CONFIG")
if not CONFIG_PATH:
    log.error("variável de ambiente TICKET_CONFIG não definida!")
    sys.exit(1)
log.info("carregando configurações de <%s>", CONFIG_PATH)
_config = ConfigParser()
_config.read(CONFIG_PATH)


def get_features():
    features = []
    for feature in _config["features"]:
        if _config.getboolean("features", feature):
            features.append(feature)
    return features


def get_priodesc():
    priodesc = {1: "Urgente", 2: "Atenção", 3: "Normal", 4: "Baixa", 5: "Baixíssima"}
    for prio in _config["priodesc"]:
        priodesc[int(prio)] = _config["priodesc"][prio]
    return priodesc


def get_priocolor():
    priocolor = {1: "#FF8D8F", 2: "#99CC00", 3: "#FF9966", 4: "#6DF2B2", 5: "#9FEFF2"}
    for prio in _config["priocolor"]:
        priocolor[int(prio)] = _config["priocolor"][prio]
    return priocolor


def cfg(section, key):
    return _config[section][str(key)]


priodesc = get_priodesc()
priocolor = get_priocolor()
features = get_features()
title = cfg("ticket", "title")
