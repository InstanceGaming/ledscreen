import logging
import logging
import os
import re
import subprocess

import database
from database import session
from models import (User,
                    UserType,
                    AuthSession,
                    generate_user_token_safe, )
from pluggram import PluggramMeta

VERSION = '1.0.0'
LOG = logging.getLogger('ledscreen.system')


def start_pluggram(pluggram: PluggramMeta) -> bool:
    pass


def pause_pluggram(pluggram: PluggramMeta, clear_screen=False):
    pass


def stop_pluggram(pluggram: PluggramMeta):
    pause_pluggram(pluggram, clear_screen=True)


USERNAME_PATTERN = re.compile('[^A-Za-z- ]+')


def validate_username(value):
    if value is not None:
        if isinstance(value, str):
            if 1 < len(value) < 40:
                if not USERNAME_PATTERN.search(value):
                    return True
    return False


def validate_password(value):
    if value is not None:
        if isinstance(value, str):
            if 6 <= len(value) < 64:
                return True
    return False


def create_user(user_type: UserType,
                user_name: str,
                expiry=None,
                password=None,
                lock=False,
                comment=None):
    uid = generate_user_token_safe()
    short_text = uid[:16]

    LOG.debug(f'creating user {short_text}')

    with session.begin():
        if user_type != UserType.STUDENT:
            lock = False

        user = User(uid,
                    user_type,
                    user_name.capitalize(),
                    expiry=expiry,
                    password=password,
                    comment=comment,
                    lock=lock)
        session.add(user)

    LOG.info(f'created user {short_text}')
    return user


def remove_user(uid: str):
    short_text = uid[:16]
    LOG.debug(f'removing user {short_text}')
    user = User.query.get(uid)

    if user is not None:
        with session.begin():
            session.delete(user)
        LOG.info(f'removed user {short_text}')
        return True
    return False


def shutdown():
    # todo: show message on screen

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
    # todo: show message on screen

    if os.name == 'posix':
        LOG.info(f'restarting...')
        proc = subprocess.Popen(['reboot'])
        proc.wait()
    else:
        raise NotImplementedError('Intentionally left unimplemented; this system is only used on Linux')


def reset():
    LOG.info(f'--- BEGINNING RESET ---')

    # 3. Purge all auth sessions
    if database.has_table(AuthSession.__tablename__):
        database.truncate_table(session, AuthSession.__tablename__)

    # 4. Remove all users
    if database.has_table(User.__tablename__):
        database.truncate_table(session, User.__tablename__, ignore_constraints=True)

    LOG.info(f'--- RESET COMPLETED ---')
