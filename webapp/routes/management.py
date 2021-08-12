import logging
from flask import Blueprint, render_template

import system
from .authentication import auth_or_login


LOG = logging.getLogger('ledscreen.web.management')
bp = Blueprint('manage', __name__, url_prefix='/manage')


@bp.route('/', methods=['GET'])
def index():
    auth_or_login()
    name = system.config['user.name']
    programs = system.loaded_pluggrams
    return render_template('pages/manage.html', programs=programs, username=name)
