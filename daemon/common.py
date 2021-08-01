from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import api

LIMITER = Limiter(key_func=get_remote_address)
CONFIG = {}
PROGRAMS = []
SCREEN = None
THREADS = []


def init_flask(app, config, programs):
    global LIMITER, CONFIG, PROGRAMS, SCREEN
    LIMITER.init_app(app)
    CONFIG = config
    PROGRAMS = programs
    SCREEN = api.Screen(
        CONFIG['screen.width'],
        CONFIG['screen.height'],
        CONFIG['screen.gpio_pin'],
        CONFIG['screen.frequency'],
        CONFIG['screen.dma_channel'],
        CONFIG['screen.max_brightness'],
        CONFIG['screen.inverted'],
        CONFIG['screen.gpio_channel']
    )


def init_minimum(config):
    global CONFIG
    CONFIG = config


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
