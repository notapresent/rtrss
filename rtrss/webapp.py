from flask import Flask

from rtrss.webapphelpers import db
from rtrss.views import blueprint


def make_app(conf):
    app = Flask(__name__)
    app.config.from_object(conf)
    db.init_app(app)
    app.register_blueprint(blueprint)
    return app

