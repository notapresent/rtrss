import logging
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from . import OperationInterruptedException

_logger = logging.getLogger(__name__)


@contextmanager
def session_scope(SessionFactory):
    """Provide a transactional scope around a series of operations."""
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
