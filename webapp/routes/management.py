import logging
from flask import Blueprint, render_template
from common import pluggram_manager
from .authentication import auth_or_login


LOG = logging.getLogger('ledscreen.web.management')
bp = Blueprint('manage', __name__, url_prefix='/manage')


@bp.route('/', methods=['GET'])
def index():
    auth_or_login()
    programs = []

    for name in pluggram_manager.get_names():
        info = pluggram_manager.get_info(name, options=True)
        programs.append(info)

    return render_template('pages/manage.html', programs=programs)
