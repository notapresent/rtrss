from flask import Flask

from rtrss.webapphelpers import db
from rtrss.views import blueprint

app = Flask(__name__)
app.config.from_object('rtrss.config')
db.init_app(app)
app.register_blueprint(blueprint)

@app.before_first_request
def setup():
    pass  # TODO cache warmup etc

