import logging
from flask import (Blueprint,
                   request,
                   render_template,
                   redirect,
                   make_response,
                   url_for,
                   abort)
import enum
import system
from common import WELCOME_TEMPLATE, SETUP_TEMPLATE
from database import session
from models import User, UserType
from .authentication import check_password, create_user_session, respond_with_cookie

LOG = logging.getLogger('ledscreen.web.oobe')
bp = Blueprint('oobe', __name__, url_prefix='/oobe')


@bp.route('/welcome', methods=['GET'])
def welcome():
    enabled = system.needs_setup()

    if enabled:
        return render_template(WELCOME_TEMPLATE)
    return abort(410)


class SetupMessage(enum.IntEnum):
    USERNAME_LENGTH = 1
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

        if len(user_name) > 40 or len(user_name) < 2:
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.USERNAME_LENGTH)

        if len(password) > 64 or len(password) < 6:
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.PASSWORD_LENGTH)

        if password != confirm_password:
            return render_template(SETUP_TEMPLATE,
                                   mid=SetupMessage.PASSWORD_CONFIRM_MISMATCH)

        user = system.create_user(UserType.ADMIN,
                                  user_name,
                                  password=password)
        sid, expiration = create_user_session(user)
        return respond_with_cookie(sid,
                                   expiration,
                                   render_template(SETUP_TEMPLATE, completed=True, uid=user.uid))
    else:
        if enabled:
            return render_template(SETUP_TEMPLATE)
    return abort(410)
