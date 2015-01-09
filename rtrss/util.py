import logging
import os
import datetime
from rtrss import config


_logger = logging.getLogger(__name__)


def save_debug_file(filename, contents):
    ts_prefix = datetime.datetime.now().strftime('%d-%m-%Y_%H_%M_%S')
    filename = "{}_{}".format(ts_prefix, filename)
    filename = os.path.join(config.DATA_DIR, filename)
    with open(filename, 'w') as f:
        f.write(contents)
