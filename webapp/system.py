import os
import re
import hmac
import utils
import logging
import subprocess
from flask import request
from common import config, screen
from typing import Optional
from datetime import datetime, timedelta


LOG = logging.getLogger('ledscreen.system')
USERNAME_PATTERN = re.compile('[^A-Za-z- ]+')
AUTH_COOKIE_NAME = 'ledscreen'
SESSION_TOKEN_LENGTH = 32


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
        self.session_token = \
            utils.generate_sanitized_alphanumerics(SESSION_TOKEN_LENGTH)
        self.expiration = (datetime.utcnow() + timedelta(minutes=config.get(
            'app.max_session_minutes')))
        self.ping()
        LOG.info(f'authenticated user with session {user_state.session_token}')

    def ping(self):
        self.last_activity = datetime.utcnow()

    def logout(self):
        LOG.info(f'unauthenticated user from session '
                 f'{user_state.session_token}')
        self.session_token = None

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
    address = request.remote_addr

    if address is None or address == '':
        address = '???.???.???.???'

    cookie_value = request.cookies.get(AUTH_COOKIE_NAME)
    LOG.info(
        f'auth check from {address} path="{request.path}" '
        f'expired={user_state.expired} token={cookie_value}')
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
        raise NotImplementedError('Intentionally left unimplemented')


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
        raise NotImplementedError('Intentionally left unimplemented')
