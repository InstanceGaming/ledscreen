import hmac
import logging
import os
import re
import subprocess
import utils
from flask import request
from datetime import datetime, timedelta
from typing import Optional, List

from api import Screen
from pluggram import PluggramMeta

VERSION = '1.0.0'
LOG = logging.getLogger('ledscreen.system')
USERNAME_PATTERN = re.compile('[^A-Za-z- ]+')
AUTH_COOKIE_NAME = 'ledscreen'
SESSION_TOKEN_LENGTH = 32

config = {}
loaded_pluggrams = []
screen: Optional[Screen] = None


class UserState:
    def __init__(self):
        self.session_token: Optional[str] = None
        self.expiration: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None

    @property
    def expired(self):
        if self.last_activity is not None and self.expiration is not None:
            if self.last_activity > self.expiration:
                return True
        return False

    def login(self):
        self.session_token = utils.generate_sanitized_alphanumerics(SESSION_TOKEN_LENGTH)
        self.expiration = datetime.utcnow() + timedelta(minutes=config.get('app.max_session_minutes'))
        self.ping()
        LOG.info(f'authenticated user with session {user_state.session_token}')

    def ping(self):
        self.last_activity = datetime.utcnow()

    def logout(self):
        self.session_token = None
        LOG.info(f'unauthenticated user from session {user_state.session_token}')

    def validate_session(self, b: str):
        if self.session_token and b:
            if self.session_token == b:
                return True

        return False


user_state = UserState()


def validate_password(value) -> bool:
    if value is not None:
        if isinstance(value, str):
            if 6 <= len(value) < 64:
                return True
    return False


def check_password(stored, given) -> bool:
    return hmac.compare_digest(stored, given)


def authenticate_user(password: str):
    if password is not None:
        config_password = config['user.password']
        if check_password(config_password, password):
            user_state.login()
            return True
    return False


def is_user_authenticated() -> bool:
    cookie_value = request.cookies.get(AUTH_COOKIE_NAME)
    LOG.debug(
        f'is_user_authenticated(): expired={user_state.expired} cookie_value={cookie_value} stored={user_state.session_token}')
    if not user_state.expired:
        if user_state.validate_session(cookie_value):
            return True
    return False


def shutdown():
    screen.clear()
    screen.set_font('default')
    screen.draw_text((0, 0),
                     0x0000FF,
                     'Poweroff',
                     anchor='lt',
                     alignment='left')

    if os.name == 'posix':
        args = ['poweroff']
        LOG.info(f'shutting down...')
        proc = subprocess.Popen(args)
        return_code = proc.wait(2)
        LOG.debug(f'poweroff return-code {return_code}')
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux, developed on '
                                  'Windows.')


def restart():
    screen.clear()
    screen.set_font('default')
    screen.draw_text((0, 0),
                     0x00FFFF,
                     'Restart',
                     anchor='lt',
                     alignment='left')

    if os.name == 'posix':
        LOG.info(f'restarting...')
        proc = subprocess.Popen(['reboot'])
        proc.wait()
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux')


def init(conf, pluggrams: List[PluggramMeta]):
    global config, loaded_pluggrams, screen
    config = conf
    loaded_pluggrams = pluggrams
    screen = Screen(
        config['screen.width'],
        config['screen.height'],
        config['screen.gpio_pin'],
        config['screen.frequency'],
        config['screen.dma_channel'],
        config['screen.brightness'],
        config['screen.inverted'],
        config['screen.gpio_channel'],
        config['screen.fonts_dir']
    )
