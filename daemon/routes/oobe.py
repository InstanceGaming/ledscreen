import logging
from flask import (Blueprint,
                   request,
                   render_template,
                   abort)
import enum
import system
from common import WELCOME_TEMPLATE, SETUP_TEMPLATE
from models import UserType, RunTarget
from .authentication import create_user_auth_session, respond_with_cookie

LOG = logging.getLogger('ledscreen.web.oobe')
bp = Blueprint('oobe', __name__, url_prefix='/oobe')


@bp.route('/welcome', methods=['GET'])
def welcome():
    enabled = system.needs_setup()

    if enabled:
        return render_template(WELCOME_TEMPLATE)
    return abort(410)


class SetupMessage(enum.IntEnum):
    BAD_USERNAME = 1
    PASSWORD_CONFIRM_MISMATCH = 2
    EMPTY_FIELD = 3
    PASSWORD_LENGTH = 4


@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    enabled = system.needs_setup()

    if request.method == 'POST':
        user_name = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')

        if password is None or confirm_password is None or user_name is None:
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.EMPTY_FIELD)

        if not system.validate_username(user_name):
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.BAD_USERNAME)

        if not system.validate_password(password):
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.PASSWORD_LENGTH)

        if password != confirm_password:
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.PASSWORD_CONFIRM_MISMATCH)

        workspace = system.create_workspace(run_privilege=RunTarget.SCREEN)
        user = system.create_user(UserType.ADMIN,
                                  user_name,
                                  workspace.wid,
                                  password=password)
        aid, expiration = create_user_auth_session(user)
        return respond_with_cookie(aid,
                                   expiration,
                                   render_template(SETUP_TEMPLATE, completed=True, uid=user.uid))
    else:
        if enabled:
            return render_template(SETUP_TEMPLATE)
    return abort(410)
