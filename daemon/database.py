from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.util import nullcontext
from sqlalchemy import text as sql_text

_raw_session = sessionmaker(autocommit=True,
                            autoflush=False)
session = scoped_session(_raw_session)

Base = declarative_base()
Base.query = session.query_property()


def init(connection_uri: str):
    # noinspection PyUnreachableCode
    if __debug__:
        engine = create_engine(connection_uri,
                               pool_pre_ping=True,
                               pool_size=5,
                               pool_recycle=1000,
                               pool_timeout=3,
                               echo=True)
    else:
        engine = create_engine(connection_uri,
                               pool_pre_ping=True,
                               pool_size=30,
                               pool_recycle=3600,
                               pool_timeout=5)
    _raw_session.configure(bind=engine)


def init_flask(app):
    def teardown_session(exception=None):
        session.remove()

    init(app.config['SQLALCHEMY_DATABASE_URI'])
    app.teardown_request(teardown_session)


def conditional_context(needed=True):
    """
    Avoid "A transaction is already begun on this Session" errors by using this context instead.
    :return: A session.begin() context or nullcontext() if aleady set.
    """
    return session.begin() if needed else nullcontext()


def execute_sql(s, statement: str):
    sql = sql_text(statement)
    return s.execute(sql)


def truncate_table(s, table_name: str, ignore_constraints=False):
    if ignore_constraints:
        execute_sql(s, 'SET FOREIGN_KEY_CHECKS=0')

    result = execute_sql(s, f'TRUNCATE TABLE {table_name}')

    if ignore_constraints:
        execute_sql(s, 'SET FOREIGN_KEY_CHECKS=1')

    return result


def has_table(name):
    b = session.get_bind()
    inspector = inspect(b)
    result = inspector.dialect.has_table(b.connect(), name)
    return result


def setup():
    b = session.get_bind()
    Base.metadata.drop_all(bind=b)
    Base.metadata.create_all(bind=b)
