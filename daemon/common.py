from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


LIMITER = Limiter(key_func=get_remote_address)
CONFIG = {}
PROGRAMS = []


def init(app, config, programs):
    global LIMITER, CONFIG, PROGRAMS
    LIMITER.init_app(app)
    CONFIG = config
    PROGRAMS = programs


LOGIN_PAGE = 'auth.login'
LOGIN_TEMPLATE = 'pages/login.html'
MANAGEMENT_PAGE = 'manage.index'
MANAGEMENT_TEMPLATE = 'pages/manage.html'
USER_WORKSPACE_PAGE = 'workspaces.workspace'
USER_WORKSPACE_TEMPLATE = 'pages/workspace.html'
SETUP_PAGE = 'oobe.setup'
SETUP_TEMPLATE = 'pages/setup.html'
WELCOME_PAGE = 'oobe.welcome'
WELCOME_TEMPLATE = 'pages/welcome.html'
