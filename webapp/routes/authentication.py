from typing import Union
from flask import (Blueprint,
                   request,
                   render_template,
                   redirect,
                   make_response,
                   url_for,
                   abort)
from models import (AuthSession,
                    User,
                    UserType,
                    generate_auth_session_token_safe,
                    lookup_aid_cs)
from datetime import datetime, timedelta
from database import session
import system
import common
import hmac
import enum
import logging

LOG = logging.getLogger('ledscreen.web.auth')
bp = Blueprint('auth', __name__)


COOKIE_KEY = 'ledscreen'
SESSION_EXP_AGE = timedelta(hours=1)


def coerce_auth_session(s):
    with session.begin():
        if isinstance(s, str):
            if len(s) != 64:
                raise ValueError('Invalid AID')
            sess = AuthSession.query.get(s)
        elif isinstance(s, AuthSession):
            sess = s
        else:
            raise TypeError('Must be a string or Session instance')
        return sess


def check_auth_session_valid(s):
    sess = coerce_auth_session(s)
    short_text = sess.aid[:16]

    if sess.expires_at > sess.issued_at:
        if sess.expires_at > datetime.utcnow():
            return True
        else:
            LOG.info(f'session validate: "{short_text}" has expired')
    else:
        LOG.warning(f'session validate: "{short_text}" has invalid expiration date')

    LOG.debug(f'session validate: not valid')
    return False


class AuthResult:

    @property
    def session(self) -> AuthSession:
        return self._auth_session

    @property
    def user(self) -> User:
        return self._user

    @property
    def active(self):
        if self._user is not None:
            return self._user.locked
        return False

    @property
    def valid(self) -> bool:
        return check_auth_session_valid(self._auth_session)

    def __init__(self, sess: AuthSession, user=None):
        assert isinstance(sess, AuthSession)
        assert isinstance(user, User)
        self._auth_session = sess
        self._user = user


def get_auth_status() -> Union[AuthResult, None]:
    cookie_value = request.cookies.get(COOKIE_KEY)

    if cookie_value is not None and len(cookie_value) > 0:
        session_entry = lookup_aid_cs(cookie_value)

        if session_entry is not None:
            user = User.query.get(session_entry.owner)

            if user is not None:
                return AuthResult(session_entry, user)
            else:
                LOG.warning(f'session "{session_entry.aid[:16]}" not associated with user')

    return None


def check_password(stored, given):
    return hmac.compare_digest(stored, given)


class LoginMessage(enum.IntEnum):
    BAD_PASSWORD = 1
    NOT_AUTHENTICATED = 2
    LOGGED_OUT = 3
    SERVER_ERROR = 4
    NO_USERS = 5


def auth_or_login(minimum_credential=None):
    result = get_auth_status()
    if result is None or not result.valid:
        return abort(redirect(url_for(common.LOGIN_PAGE,
                                      mid=int(LoginMessage.NOT_AUTHENTICATED),
                                      next=request.full_path)))

    if minimum_credential is not None:
        if int(result.user.type) < minimum_credential:
            return abort(403)

    return result


def auth_endpoint_allowed(minimum_credential=None):
    result = get_auth_status()

    if result is not None:
        if minimum_credential is not None:
            if int(result.user.type) < minimum_credential:
                return False
        return True

    return False


@bp.route('/logout', methods=['GET'])
def logout():
    cookie_value = request.cookies.get(COOKIE_KEY)

    if cookie_value is not None and len(cookie_value) > 0:
        session_entry = lookup_aid_cs(cookie_value)
        if session_entry is not None:
            with session.begin():
                user = User.query.get(session_entry.owner)
                user.logout_at = datetime.utcnow()
                delta = user.logout_at - user.login_at
                user.online_duration = delta.total_seconds()

                LOG.info(f'logging out {user.uid} from session {session_entry.aid[:16]}')
                session.delete(session_entry)

            return redirect(url_for(common.LOGIN_PAGE, mid=int(LoginMessage.LOGGED_OUT)))

    # default
    return redirect(url_for(common.LOGIN_PAGE))


def create_user_auth_session(user, auth_result=None):
    with session.begin():
        if auth_result is not None and auth_result.valid:
            session.remove(auth_result.session)

    aid = generate_auth_session_token_safe()

    with session.begin():
        current_time = datetime.utcnow()
        expiration = current_time + SESSION_EXP_AGE
        session_entry = AuthSession(aid, user.uid, expiration)
        session.add(session_entry)
        user.login_at = current_time
        user.login_count = user.login_count + 1

    LOG.info(f'authenticated {user.uid} with session {aid[:16]}')

    return aid, expiration


def respond_with_cookie(aid, expiration, *content):
    response = make_response(*content)
    response.set_cookie(COOKIE_KEY,
                        aid,
                        expires=expiration,
                        samesite='Strict')
    return response


@bp.route('/', methods=['GET', 'POST'])
def login():
    template_path = common.LOGIN_TEMPLATE
    mid_parameter = request.args.get('mid')
    default_mid = None

    if mid_parameter is not None:
        try:
            default_mid = int(mid_parameter)
        except ValueError:
            LOG.debug('non-integer value passed as MID parameter')
            default_mid = None

    next_parameter = request.args.get('next')

    auth_result = get_auth_status()
    if auth_result is not None and auth_result.valid:
        redirect(common.MANAGEMENT_PAGE)
        pass

    if request.method == 'POST':
        password = request.form.get('password')

        if system.validate_password(password):
            with session.begin():
                user = User.query.filter_by(UserType.ADMIN).first()

            if user is not None:
                if user.password is not None:
                    if password is None or len(password) < 1:
                        return render_template(template_path,
                                               mid=LoginMessage.PASSWORD_REQUIRED)
                    else:
                        if not check_password(user.password, password):
                            return render_template(template_path,
                                                   mid=LoginMessage.BAD_PASSWORD)

                aid, expiration = create_user_auth_session(user)

                if next_parameter is None:
                    response = respond_with_cookie(aid, expiration, redirect(common.MANAGEMENT_PAGE))
                else:
                    LOG.debug(f'redirecting according to next parameter "{next_parameter}"')
                    response = respond_with_cookie(aid, expiration, redirect(next_parameter))
                return response
            else:
                return render_template(template_path,
                                       mid=LoginMessage.NO_USERS)
        else:
            return render_template(template_path,
                                   mid=LoginMessage.BAD_PASSWORD)
    # default
    return render_template(template_path, mid=default_mid)
