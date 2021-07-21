from datetime import datetime as dt
from typing import Union
from flask_sqlalchemy import SQLAlchemy
from utils import generate_sanitized_alphanumerics, generate_url_binary
from sqlalchemy import func
import enum
import logging

db = SQLAlchemy()
SESSION_TOKEN_LENGTH = 64
WORKSPACE_TOKEN_LENGTH = 32
USER_TOKEN_LENGTH = 8


def create_all_tables(app):
    global db
    db.init_app(app)
    with app.app_context():
        db.create_all()


def init(app):
    global db
    db.init_app(app)


class UserType(enum.IntEnum):
    STUDENT = 0
    ADMIN = 1
    SYSTEM = 3


class User(db.Model):
    __tablename__ = 'users'

    @property
    def locked(self):
        return self.locked_at is not None

    uid = db.Column(db.String(8), primary_key=True)
    issued_at = db.Column(db.DateTime(), nullable=False)
    type = db.Column(db.Enum(UserType), nullable=False)
    user_name = db.Column(db.Unicode(40), nullable=False)
    expires_at = db.Column(db.DateTime(), nullable=True)
    locked_at = db.Column(db.DateTime(), nullable=True)
    password = db.Column(db.Unicode(64), nullable=True)
    login_at = db.Column(db.DateTime(), nullable=True)
    logout_at = db.Column(db.DateTime(), nullable=True)
    admin_comment = db.Column(db.UnicodeText(), nullable=True)

    def __init__(self,
                 uid: str,
                 type: UserType,
                 user_name: str,
                 expiry=None,
                 password=None,
                 lock=False,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.uid = uid
        self.issued_at = current_datetime
        self.type = type
        self.user_name = user_name
        self.expires_at = expiry
        self.password = password

        if lock:
            self.locked_at = current_datetime

    def __repr__(self):
        return f'<User {self.uid} name="{self.user_name}" type={self.type.name}>'


class Session(db.Model):
    __tablename__ = 'sessions'
    sid = db.Column(db.String(64), primary_key=True)
    issued_at = db.Column(db.DateTime(), nullable=False)
    expires_at = db.Column(db.DateTime(), nullable=False)

    owner = db.Column(db.String(8),
                      db.ForeignKey('users.uid', onupdate="CASCADE", ondelete="CASCADE"),
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
    SIM = 1
    SCREEN = 2


class RunStatus(enum.IntEnum):
    IDLE = 0
    STARTING = 1
    RUNNING = 1
    STOPPING = 2


class Workspace(db.Model):
    __tablename__ = 'workspaces'

    @property
    def short_wid(self):
        return self.wid[:16]

    wid = db.Column(db.String(32), primary_key=True)
    created_at = db.Column(db.DateTime(), nullable=False)
    env_path = db.Column(db.UnicodeText(), nullable=False)
    storage_path = db.Column(db.UnicodeText(), nullable=False)
    run_dir = db.Column(db.UnicodeText(), nullable=False)
    interpreter_path = db.Column(db.UnicodeText(), nullable=False)
    py_file = db.Column(db.UnicodeText(), nullable=False)
    run_privilege = db.Column(db.Enum(RunTarget), nullable=True)
    max_runtime = db.Column(db.Integer(), nullable=True)
    run_target = db.Column(db.Enum(RunTarget), nullable=True)
    run_status = db.Column(db.Enum(RunStatus), nullable=False, server_default=RunStatus.IDLE.name)
    opened_at = db.Column(db.DateTime(), nullable=True)

    owner = db.Column(db.String(8),
                      db.ForeignKey('users.uid', onupdate="CASCADE", ondelete="SET NULL"),
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


class RunLog(db.Model):
    __tablename__ = 'run_log'

    @property
    def short_rid(self):
        return self.rid[:16]

    rid = db.Column(db.String(64), primary_key=True)
    started_at = db.Column(db.DateTime(), nullable=False)
    stopped_at = db.Column(db.DateTime(), nullable=True)
    return_code = db.Column(db.Integer(), nullable=True)
    std_out = db.Column(db.UnicodeText(), nullable=True)
    std_error = db.Column(db.UnicodeText(), nullable=True)
    exit_reason = db.Column(db.Enum(ExitReason), nullable=True)
    interpreter_path = db.Column(db.UnicodeText(), nullable=False)
    run_path = db.Column(db.UnicodeText(), nullable=False)

    owner = db.Column(db.String(8),
                      db.ForeignKey('users.uid', onupdate="CASCADE", ondelete="SET NULL"),
                      nullable=True)
    workspace = db.Column(db.String(32),
                          db.ForeignKey('workspaces.wid', onupdate="CASCADE", ondelete="SET NULL"),
                          nullable=True)

    def __init__(self,
                 rid: str,
                 interpreter_path: str,
                 run_path: str,
                 user=None,
                 workspace=None,
                 datetime=None):
        current_datetime = datetime or dt.utcnow()

        self.rid = rid
        self.interpreter_path = interpreter_path
        self.run_path = run_path
        self.user = user
        self.workspace = workspace
        self.started_at = current_datetime

    def __repr__(self):
        return f'<RunLog {self.short_rid} run_path={self.py_file} user={self.user} workspace={self.workspace}>'


def lookup_sid_cs(input_sid: str) -> Union[None, Session]:
    """
    Case-sensitive session ID lookup.
    :param input_sid: proposed session ID code
    :return: Session instance or None
    """
    return Session.query.filter(Session.sid == func.binary(input_sid)).first()


def generate_session_token_safe():
    result = generate_sanitized_alphanumerics(SESSION_TOKEN_LENGTH, special=True)

    if lookup_sid_cs(result) is not None:
        logging.info('one in a zillion just happened!')
        return generate_session_token_safe()

    return result


def generate_workspace_token_safe():
    result = generate_url_binary(WORKSPACE_TOKEN_LENGTH)

    if lookup_wid_cs(result) is not None:
        logging.info('one in a zillion just happened!')
        return generate_workspace_token_safe()

    return result


def generate_user_token_safe():
    result = generate_sanitized_alphanumerics(USER_TOKEN_LENGTH, lowercase=False)

    if User.query.get(result) is not None:
        logging.info('one in a zillion just happened!')
        return generate_user_token_safe()

    return result
