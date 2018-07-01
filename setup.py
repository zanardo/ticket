from setuptools import setup
from ticket import __version__


setup(
    name="ticket",
    version=__version__,
    packages=["ticket"],
    install_requires=[
        "zpgdb==0.4.2",
        "bottle==0.12.13",
        "gunicorn",
        "setproctitle",
    ],
)
