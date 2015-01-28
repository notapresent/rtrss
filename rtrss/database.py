import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from rtrss.exceptions import OperationInterruptedException
from rtrss import config


_logger = logging.getLogger(__name__)

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI,
    echo=False,
    client_encoding='utf8'
)

Session = sessionmaker(bind=engine)


@contextmanager
def session_scope(sessionfactory=None):
    """Provide a transactional scope around a series of operations."""
    if sessionfactory is None:
        sessionfactory = Session

    session = scoped_session(sessionfactory)
    try:
        yield session
    except SQLAlchemyError as e:
        message = "Database error: {}".format(e)
        _logger.error(message)
        session.rollback()
        raise OperationInterruptedException(message)
    else:
        session.commit()
    finally:
        session.close()


def init(eng=None):
    _logger.info('Initializing database')

    if eng is None:
        eng = engine

    from rtrss.models import Base
    Base.metadata.create_all(bind=eng)


def clear(eng=None):
    _logger.info('Clearing database')

    if eng is None:
        eng = engine
    from rtrss.models import Base

    Base.metadata.drop_all(bind=eng)
