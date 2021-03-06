import csv
import logging
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, exists, select
from sqlalchemy.schema import CreateSchema, DropSchema

from rtrss.exceptions import OperationInterruptedException
from rtrss import config


SCHEMA_NAME = 'public'

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
    if not schema_exists(SCHEMA_NAME):
        eng.execute(CreateSchema(SCHEMA_NAME))
    from rtrss.models import Base
    Base.metadata.create_all(bind=eng)


def clear(eng=None):
    _logger.info('Clearing database')

    if eng is None:
        eng = engine
    if schema_exists(SCHEMA_NAME):
        eng.execute(DropSchema(SCHEMA_NAME, cascade=True))


def import_users(filename):
    """Import user account from CSV file, skipping existing users"""
    from rtrss.models import User

    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile, skipinitialspace=True)
        lines = [line for line in reader]

    _logger.info("Importing {} accounts from {}".format(len(lines), filename))

    added = 0
    with session_scope() as db:
        for fields in lines:
            fields['id'] = int(fields['id'])
            fields['downloads_limit'] = int(fields['downloads_limit'])
            existing_user = db.query(User).get(fields['id'])

            if existing_user:
                continue

            user = User(**fields)

            db.add(user)
            added += 1

    _logger.info("%d users added, %d skipped", added, len(lines) - added)


def schema_exists(name):
    query = (
        exists(select(["schema_name"]).
               select_from("information_schema.schemata")
               .where("schema_name = 'public'"))
    )
    sess = Session()
    result = sess.query(query).scalar()
    sess.close()
    return result
