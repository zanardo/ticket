from setuptools import setup
from ticket import __version__


setup(
    name="ticket",
    version=__version__,
    packages=["ticket"],
    install_requires=["bottle==0.12.18"],
)
