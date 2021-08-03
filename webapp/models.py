from datetime import datetime as dt
from typing import Union
from utils import generate_sanitized_alphanumerics
from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        DateTime,
                        Enum,
                        UnicodeText,
                        Unicode,
                        func,
                        Boolean)
from database import Base, session
import enum
import logging

LOG = logging.getLogger('ledscreen.models')

SESSION_TOKEN_LENGTH = 64
USER_TOKEN_LENGTH = 8


class UserType(enum.IntEnum):
    STUDENT = 0
    ADMIN = 1
    SYSTEM = 3


class User(Base):
    __tablename__ = 'users'

    @property
    def locked(self):
        return self.locked_at is not None

    uid = Column(String(8), primary_key=True)
    issued_at = Column(DateTime(), nullable=False)
    type = Column(Enum(UserType), nullable=False)
    user_name = Column(Unicode(40), nullable=False)
    expires_at = Column(DateTime(), nullable=True)
    locked_at = Column(DateTime(), nullable=True)
    password = Column(Unicode(64), nullable=True)
    login_at = Column(DateTime(), nullable=True)
    logout_at = Column(DateTime(), nullable=True)
    login_count = Column(Integer(), nullable=False, default=0)
    online_duration = Column(Integer(), nullable=False, default=0)
    admin_comment = Column(UnicodeText(), nullable=True)

    def __init__(self,
                 uid: str,
                 type: UserType,
                 user_name: str,
                 expiry=None,
                 password=None,
                 lock=False,
                 comment=None,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.uid = uid
        self.issued_at = current_datetime
        self.type = type
        self.user_name = user_name.strip()
        self.expires_at = expiry
        self.password = password
        self.admin_comment = comment

        if lock:
            self.locked_at = current_datetime

    def __repr__(self):
        return f'<User {self.uid} name="{self.user_name}" type={self.type.name}>'


class AuthSession(Base):
    __tablename__ = 'auth_sessions'

    aid = Column(String(64), primary_key=True)
    issued_at = Column(DateTime(), nullable=False)
    expires_at = Column(DateTime(), nullable=False)

    owner = Column(String(8),
                   ForeignKey('users.uid', onupdate="CASCADE", ondelete="CASCADE"),
                   nullable=False)

    def __init__(self,
                 aid: str,
                 owner: str,
                 expires_at,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.aid = aid
        self.owner = owner
        self.issued_at = current_datetime
        self.expires_at = expires_at

    def __repr__(self):
        return f'<Session {self.aid} owner={self.owner}>'


class PluggramData(Base):
    __tablename__ = 'pluggram_data'

    path = Column(UnicodeText(), primary_key=True)
    started_at = Column(DateTime(), nullable=False)
    stopped_at = Column(DateTime(), nullable=True)
    run_count = Column(Integer(), nullable=False, default=0)
    startup = Column(Boolean(), nullable=False, default=False)
    clear = Column(Boolean(), nullable=False, default=True)
    settings = Column(UnicodeText(), nullable=False, server_default='{}')

    def __init__(self,
                 path: str,
                 startup=False,
                 clear=False):
        self.path = path
        self.startup = startup
        self.clear = clear

    def __repr__(self):
        return f'<PluggramModel {self.path} startup={self.startup}>'


def lookup_aid_cs(input_aid: str) -> Union[None, AuthSession]:
    """
    Case-sensitive auth ID lookup.
    :param input_aid: proposed auth ID code
    :return: Session instance or None
    """
    with session.begin():
        return AuthSession.query.filter(AuthSession.aid == func.binary(input_aid)).first()


def generate_auth_session_token_safe():
    result = generate_sanitized_alphanumerics(SESSION_TOKEN_LENGTH, special=True)

    if lookup_aid_cs(result) is not None:
        LOG.info('one in a zillion just happened!')
        return generate_auth_session_token_safe()

    return result


def generate_user_token_safe():
    result = generate_sanitized_alphanumerics(USER_TOKEN_LENGTH, lowercase=False)

    with session.begin():
        exists = User.query.get(result) is not None

    if exists:
        LOG.info('one in a zillion just happened!')
        return generate_user_token_safe()

    return result
