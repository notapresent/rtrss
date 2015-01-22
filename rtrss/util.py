import csv
import logging
import os
import datetime

from rtrss import config
from rtrss.models import User
from rtrss.database import session_scope


_logger = logging.getLogger(__name__)


def save_debug_file(filename, contents):
    ts_prefix = datetime.datetime.now().strftime('%d-%m-%Y_%H_%M_%S')
    filename = "{}_{}".format(ts_prefix, filename)
    filename = os.path.join(config.DATA_DIR, filename)
    with open(filename, 'w') as f:
        f.write(contents)

def import_users(filename):
    """Import user account from CSV file, skipping existing users"""
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile, skipinitialspace=True)
        lines = [line for line in reader]

    _logger.info("Importing {} accounts from {}".format(filename, len(lines)))

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
