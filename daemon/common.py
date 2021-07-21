from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _true():
    return True


# noinspection PyTypeChecker
LIMITER = Limiter(key_func=get_remote_address, default_limits_exempt_when=_true)

CONFIG = {}
PROGRAMS = []


def init(app, config, progs):
    global LIMITER, CONFIG, PROGRAMS
    LIMITER.init_app(app)
    CONFIG = config
    PROGRAMS = progs


LOGIN_PAGE = 'auth.login'
LOGIN_TEMPLATE = 'pages/login.html'
MANAGEMENT_PAGE = 'manage.index'
MANAGEMENT_TEMPLATE = 'pages/manage.html'
USER_WORKSPACE_PAGE = 'workspaces.workspace'
USER_WORKSPACE_TEMPLATE = 'pages/workspace.html'
