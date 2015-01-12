import os
from flask import Flask, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('rtrss.config')
db = SQLAlchemy(app)


@app.before_first_request
def setup():
    pass
    # Recreate database each time for demo
    # Base.metadata.drop_all(bind=db.engine)
    # Base.metadata.create_all(bind=db.engine)


@app.route('/')
def root():
    # users = db.session.query(User).all()
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(os.environ.get('IP', '0.0.0.0'), int(os.environ.get('PORT', 8080)))
