import enum
import system
import logging
from flask import (Blueprint,
                   abort,
                   request,
                   url_for,
                   redirect,
                   make_response,
                   render_template)


LOG = logging.getLogger('ledscreen.web.auth')
bp = Blueprint('auth', __name__)


class LoginMessage(enum.IntEnum):
    BAD_PASSWORD = 1
    LOGGED_OUT = 2
    SERVER_ERROR = 3
    NOT_AUTHENTICATED = 4


def auth_or_login():
    if not system.is_user_authenticated():
        return abort(redirect(url_for('auth.login',
                                      mid=int(LoginMessage.NOT_AUTHENTICATED))))
    else:
        system.user_state.ping()


@bp.route('/logout', methods=['GET'])
def logout():
    system.user_state.logout()

    # default
    return render_template('pages/login.html', mid=int(LoginMessage.LOGGED_OUT))


@bp.route('/', methods=['GET', 'POST'])
def login():
    mid_parameter = request.args.get('mid')
    default_mid = None

    if mid_parameter is not None:
        try:
            default_mid = int(mid_parameter)
        except ValueError:
            LOG.debug('non-integer value passed as MID parameter')
            default_mid = None

    if system.is_user_authenticated():
        return redirect(url_for('manage.index'))

    if request.method == 'POST':
        password = request.form.get('password')

        if system.authenticate_user(password):
            response = make_response(redirect(url_for('manage.index')))
            response.set_cookie(system.AUTH_COOKIE_NAME,
                                system.user_state.session_token,
                                expires=system.user_state.expiration,
                                samesite='Strict')
            return response
        else:
            default_mid = int(LoginMessage.BAD_PASSWORD)

    # default
    return render_template('pages/login.html', mid=default_mid)
