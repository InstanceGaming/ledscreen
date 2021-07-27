from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.util import nullcontext

_raw_session = sessionmaker(autocommit=True,
                            autoflush=False)
session = scoped_session(_raw_session)

Base = declarative_base()
Base.query = session.query_property()


def init(connection_uri: str):
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


def create_tables():
    b = session.get_bind()
    Base.metadata.drop_all(bind=b)
    Base.metadata.create_all(bind=b)
