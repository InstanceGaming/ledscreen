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

    LOG.debug(f'requesting program info for management page...')
    names = pluggram_manager.get_names()
    LOG.debug(f'got list of {len(names)} pluggram names')

    for name in names:
        LOG.debug(f'retrieving info for "{name}"')
        info = pluggram_manager.get_info(name, options=True)
        LOG.debug(f'retrieved program info for "{name}"')
        programs.append(info)

    return render_template('pages/manage.html', programs=programs)
