from datetime import datetime as dt
from typing import Union
from utils import generate_sanitized_alphanumerics, generate_url_binary
from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        DateTime,
                        Enum,
                        UnicodeText,
                        Unicode,
                        func)
from database import Base, session
import enum
import logging

LOG = logging.getLogger('ledscreen.models')


SESSION_TOKEN_LENGTH = 64
RUN_LOG_TOKEN_LENGTH = 64
WORKSPACE_TOKEN_LENGTH = 32
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


class Session(Base):
    __tablename__ = 'sessions'
    sid = Column(String(64), primary_key=True)
    issued_at = Column(DateTime(), nullable=False)
    expires_at = Column(DateTime(), nullable=False)

    owner = Column(String(8),
                   ForeignKey('users.uid', onupdate="CASCADE", ondelete="CASCADE"),
                   nullable=False)

    def __init__(self,
                 sid: str,
                 owner: str,
                 expires_at,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.sid = sid
        self.owner = owner
        self.issued_at = current_datetime
        self.expires_at = expires_at

    def __repr__(self):
        return f'<Session {self.sid} owner={self.owner}>'


class RunTarget(enum.IntEnum):
    SIMULATE = 1
    SCREEN = 2


class RunStatus(enum.IntEnum):
    IDLE = 0
    STARTING = 1
    RUNNING = 1
    STOPPING = 2


class Workspace(Base):
    __tablename__ = 'workspaces'

    @property
    def short_wid(self):
        return self.wid[:16]

    wid = Column(String(32), primary_key=True)
    created_at = Column(DateTime(), nullable=False)
    env_path = Column(UnicodeText(), nullable=False)
    storage_path = Column(UnicodeText(), nullable=False)
    run_dir = Column(UnicodeText(), nullable=False)
    interpreter_path = Column(UnicodeText(), nullable=False)
    py_file = Column(UnicodeText(), nullable=False)
    run_privilege = Column(Enum(RunTarget), nullable=True)
    max_runtime = Column(Integer(), nullable=True)
    run_target = Column(Enum(RunTarget), nullable=True)
    run_status = Column(Enum(RunStatus), nullable=False, server_default=RunStatus.IDLE.name)

    owner = Column(String(8),
                   ForeignKey('users.uid', onupdate="CASCADE", ondelete="SET NULL"),
                   nullable=True)

    def __init__(self,
                 wid: str,
                 env_path: str,
                 storage_path: str,
                 run_dir: str,
                 interpreter_path: str,
                 py_file: str,
                 owner=None,
                 run_privilege=None,
                 max_runtime=None,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.wid = wid
        self.created_at = current_datetime
        self.env_path = env_path
        self.storage_path = storage_path
        self.run_dir = run_dir
        self.interpreter_path = interpreter_path
        self.py_file = py_file
        self.owner = owner
        self.run_privilege = run_privilege
        self.max_runtime = max_runtime

    def __repr__(self):
        return f'<Workspace {self.short_wid} storage="{self.storage_path}" env="{self.env_path}">'


class ExitReason(enum.IntEnum):
    SYSTEM = 0
    NATURAL = 1
    ADMIN = 2
    TIMEOUT = 3


class RunLog(Base):
    __tablename__ = 'run_log'

    @property
    def short_rid(self):
        return self.rid[:16]

    rid = Column(String(64), primary_key=True)
    started_at = Column(DateTime(), nullable=False)
    stopped_at = Column(DateTime(), nullable=True)
    return_code = Column(Integer(), nullable=True)
    std_out = Column(UnicodeText(), nullable=True)
    std_error = Column(UnicodeText(), nullable=True)
    exit_reason = Column(Enum(ExitReason), nullable=True)
    interpreter_path = Column(UnicodeText(), nullable=False)
    run_path = Column(UnicodeText(), nullable=False)
    pid = Column(Integer(), nullable=False)

    owner = Column(String(8),
                   ForeignKey('users.uid', onupdate="CASCADE", ondelete="SET NULL"),
                   nullable=True)
    workspace = Column(String(32),
                       ForeignKey('workspaces.wid', onupdate="CASCADE", ondelete="SET NULL"),
                       nullable=True)

    def __init__(self,
                 rid: str,
                 pid: int,
                 interpreter_path: str,
                 run_path: str,
                 user=None,
                 workspace=None,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.rid = rid
        self.pid = pid
        self.interpreter_path = interpreter_path
        self.run_path = run_path
        self.user = user
        self.workspace = workspace
        self.started_at = current_datetime

    def __repr__(self):
        return f'<RunLog {self.short_rid} pid={self.pid} run_path={self.py_file} user={self.user} workspace={self.workspace}>'


def lookup_sid_cs(input_sid: str) -> Union[None, Session]:
    """
    Case-sensitive session ID lookup.
    :param input_sid: proposed session ID code
    :return: Session instance or None
    """
    with session.begin():
        return Session.query.filter(Session.sid == func.binary(input_sid)).first()


def lookup_rid_cs(input_rid: str) -> Union[None, RunLog]:
    """
    Case-sensitive run log ID lookup.
    :param input_rid: proposed run log ID
    :return: RunLog instance or None
    """
    with session.begin():
        return RunLog.query.filter(RunLog.rid == func.binary(input_rid)).first()


def generate_run_log_token_safe():
    result = generate_sanitized_alphanumerics(RUN_LOG_TOKEN_LENGTH, special=True)

    if lookup_rid_cs(result) is not None:
        LOG.info('one in a zillion just happened!')
        return generate_run_log_token_safe()

    return result


def generate_session_token_safe():
    result = generate_sanitized_alphanumerics(SESSION_TOKEN_LENGTH, special=True)

    if lookup_sid_cs(result) is not None:
        LOG.info('one in a zillion just happened!')
        return generate_session_token_safe()

    return result


def generate_workspace_token_safe():
    result = generate_url_binary(WORKSPACE_TOKEN_LENGTH)

    with session.begin():
        exists = Workspace.query.get(result) is not None

    if exists:
        LOG.info('one in a zillion just happened!')
        return generate_workspace_token_safe()

    return result


def generate_user_token_safe():
    result = generate_sanitized_alphanumerics(USER_TOKEN_LENGTH, lowercase=False)

    with session.begin():
        exists = User.query.get(result) is not None

    if exists:
        LOG.info('one in a zillion just happened!')
        return generate_user_token_safe()

    return result
