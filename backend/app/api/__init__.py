from flask import Blueprint

simtwit_bp = Blueprint('simtwit', __name__)

from . import routes  # noqa: E402, F401
