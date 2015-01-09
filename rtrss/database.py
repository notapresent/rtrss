import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from rtrss import OperationInterruptedException
from rtrss import config

_logger = logging.getLogger(__name__)
engine = create_engine(config.SQLALCHEMY_DATABASE_URI,  client_encoding='utf8')
Session = sessionmaker(bind=engine)


@contextmanager
def session_scope(SessionFactory=None):
    """Provide a transactional scope around a series of operations."""
    if SessionFactory is None:
        SessionFactory = Session

    session = SessionFactory()
    try:
        yield session
    except SQLAlchemyError as e:
        _logger.error("Database error %s", e)
        session.rollback()
        raise OperationInterruptedException(e)
    else:
        session.commit()
    finally:
        session.close()


def init_db(conn=None):
    from .models import Base
    if conn is None:
        from worker import engine as conn

    Base.metadata.create_all(bind=conn)


def clear_db(conn=None):
    from .models import Base
    if conn is None:
        from worker import engine as conn

    Base.metadata.drop_all(bind=conn)
