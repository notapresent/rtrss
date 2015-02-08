import logging
import os

from flask import Flask

_logger = logging.getLogger(__name__)

from rtrss.webapphelpers import db
from rtrss.views import blueprint


def make_app(conf):
    app = Flask(__name__)
    app.config.from_object(conf)
    db.init_app(app)
    app.register_blueprint(blueprint)
    _logger.info('pid:{} Webapp instance created'.format(os.getpid()))
    return app
