"""Top-level package for grbLC submodule."""

__author__ = """Sam Young"""
__email__ = "youngsam@sas.upenn.edu"
__version__ = "0.0.5"

from . import convert, fitting, search  # noqa F401
from .fitting import Model, Lightcurve, OutlierPlot
from .fitting.model import Models
from .convert import toFlux, get_dir, set_dir, convertGRB
from .search import ads, gcn
