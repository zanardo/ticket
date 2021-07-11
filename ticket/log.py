"""
Este módulo exporta o objeto "log", usado para logging nos outros módulos da aplicação.
"""

import logging

log = logging.getLogger(__name__)
logFormat = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d %(levelname).3s | %(name)s | %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
)
log.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler()
logHandler.setFormatter(logFormat)
log.addHandler(logHandler)
