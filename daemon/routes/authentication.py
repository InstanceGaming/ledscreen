from typing import Union
from flask import (Blueprint,
                   request,
                   render_template,
                   redirect,
                   make_response,
                   url_for,
                   abort)
from models import (Session,
                    User,
                    UserType,
                    Workspace,
                    generate_session_token_safe,
                    lookup_sid_cs)
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


def check_user_valid(user: User):
    if not user.locked:
        if user.expires_at is None:
            return True

        if datetime.utcnow() > user.expires_at:
            LOG.debug(f'user validate: "{user.uid}" has expired')
        else:
            return True
    else:
        LOG.debug(f'user validate: "{user.uid}" is locked')

    return False


def check_session_valid(s: Session):
    short_text = s.sid[:16]

    if s.expires_at > s.issued_at:
        if s.expires_at > datetime.utcnow():
            return True
        else:
            LOG.info(f'session validate: "{short_text}" has expired')
    else:
        LOG.warning(f'session validate: "{short_text}" has invalid expiration date')

    LOG.debug(f'session validate: not valid')
    return False


class AuthResult:

    @property
    def session(self) -> Session:
        return self._session

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
        return check_session_valid(self._session) and check_user_valid(self._user)

    def __init__(self, session: Session, user=None):
        assert isinstance(session, Session)
        assert isinstance(user, User)
        self._session = session
        self._user = user


def get_auth_status() -> Union[AuthResult, None]:
    cookie_value = request.cookies.get(COOKIE_KEY)

    if cookie_value is not None and len(cookie_value) > 0:
        session_entry = lookup_sid_cs(cookie_value)

        if session_entry is not None:
            user = User.query.get(session_entry.owner)

            if user is not None:
                return AuthResult(session_entry, user)
            else:
                LOG.warning(f'session "{session_entry.sid[:16]}" not associated with user')

    return None


def get_home_url(user: User):
    if user.type == UserType.ADMIN:
        return url_for(common.MANAGEMENT_PAGE)
    elif user.type == UserType.STUDENT:
        workspace = Workspace.query.filter_by(owner=user.uid).first()

        if workspace is not None:
            return url_for(common.USER_WORKSPACE_PAGE, wid=workspace.wid)
        else:
            LOG.warning(f'user "{user.uid}" has no workspace')
    return None


def check_password(stored, given):
    return hmac.compare_digest(stored, given)


class LoginMessage(enum.IntEnum):
    BAD_CODE = 1
    BAD_PASSWORD = 2
    LOCKED_OUT = 3
    NOT_AUTHENTICATED = 4
    PASSWORD_REQUIRED = 5
    NO_HOME = 6
    LOGGED_OUT = 7
    ARCHIVED = 8
    SERVER_ERROR = 9
    RATE_LIMIT = 10


def redirect_home(user: User):
    destination = get_home_url(user)

    if destination is not None:
        return redirect(destination)

    LOG.debug(f'login page redirect skipped for user {user.uid}')
    return render_template(common.LOGIN_TEMPLATE, mid=LoginMessage.NO_HOME)


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
        session_entry = lookup_sid_cs(cookie_value)
        if session_entry is not None:
            with session.begin():
                user = User.query.get(session_entry.owner)
                user.logout_at = datetime.utcnow()
                delta = user.logout_at - user.login_at
                user.online_duration = delta.total_seconds()

                LOG.info(f'logging out {user.uid} from session {session_entry.sid[:16]}')
                session.delete(session_entry)
            return redirect(url_for(common.LOGIN_PAGE, mid=int(LoginMessage.LOGGED_OUT)))

    # default
    return redirect(url_for(common.LOGIN_PAGE))


def create_user_session(user, auth_result=None):
    with session.begin():
        if auth_result is not None and auth_result.valid:
            session.remove(auth_result.session)

    sid = generate_session_token_safe()

    with session.begin():
        current_time = datetime.utcnow()
        expiration = current_time + SESSION_EXP_AGE
        session_entry = Session(sid, user.uid, expiration)
        session.add(session_entry)
        user.login_at = current_time
        user.login_count = user.login_count + 1

    LOG.info(f'authenticated {user.uid} with session {sid[:16]}')

    return sid, expiration


def respond_with_cookie(sid, expiration, *content):
    response = make_response(*content)
    response.set_cookie(COOKIE_KEY,
                        sid,
                        expires=expiration,
                        samesite='Strict')
    return response


@bp.route('/', methods=['GET', 'POST'])
@common.LIMITER.limit('10/minute', error_message='Please wait and try again later.')
def login():
    if system.needs_setup():
        return redirect(url_for(common.WELCOME_PAGE))
    else:
        template_path = common.LOGIN_TEMPLATE
        mid_parameter = request.args.get('mid')
        code_paremeter = request.args.get('code')
        default_mid = None

        if mid_parameter is not None:
            try:
                default_mid = int(mid_parameter)
            except ValueError:
                LOG.debug('non-integer value passed as MID parameter')
                pass

        next_parameter = request.args.get('next')

        auth_result = get_auth_status()
        if auth_result is not None and auth_result.valid:
            return redirect_home(auth_result.user)

        if request.method == 'POST':
            form_code = request.form.get('code')
            LOG.debug(f'attempting login using code "{form_code}"')

            if form_code is not None and len(form_code) == 8:
                with session.begin():
                    user = User.query.get(form_code)

                if user is not None:
                    user_valid = check_user_valid(user)
                    if user_valid:
                        if user.password is not None:
                            form_password = request.form.get('password')

                            if form_password is None or len(form_password) < 1:
                                return render_template(template_path,
                                                       mid=LoginMessage.PASSWORD_REQUIRED,
                                                       fill_code=form_code)
                            else:
                                if not check_password(user.password, form_password):
                                    return render_template(template_path,
                                                           mid=LoginMessage.BAD_PASSWORD,
                                                           fill_code=form_code)

                        sid, expiration = create_user_session(user)

                        if next_parameter is None:
                            destination = get_home_url(user)
                            if destination is None:
                                response = respond_with_cookie(sid, expiration, 500)
                            else:
                                response = respond_with_cookie(sid, expiration, redirect(destination))
                        else:
                            LOG.debug(f'redirecting according to next parameter "{next_parameter}"')
                            response = respond_with_cookie(sid, expiration, redirect(next_parameter))
                        return response
                    else:
                        if user.locked:
                            render_template(template_path, mid=LoginMessage.LOCKED_OUT, msg=user.status_message)
            # invalid code length/none, user does not exist, user is invalid
            return render_template(template_path, mid=LoginMessage.BAD_CODE)

        # default
        return render_template(template_path, mid=default_mid, fill_code=code_paremeter)
