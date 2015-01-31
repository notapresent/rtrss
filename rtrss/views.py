# -*- coding: utf-8 -*-
import os
import datetime
from functools import wraps

from flask import (send_from_directory, render_template, make_response, abort,
                   Response, request, blueprints)

from rtrss import config
from rtrss.filestorage import make_storage
from rtrss.webapphelpers import (make_category_tree, get_feed_data,
                                 check_auth)


blueprint = blueprints.Blueprint('views', __name__)


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


@blueprint.route('/')
def index():
    tree = make_category_tree()
    return render_template('index.html', tree=tree)


@blueprint.route('/torrent/<int:torrent_id>')
def torrent(torrent_id):
    # TODO add user passkey support
    storage = make_storage(config)
    torrentfile = storage.get(config.TORRENT_PATH_PATTERN.format(torrent_id))

    if torrentfile:
        fn = '{}.torrent'.format(torrent_id)
        resp = make_response(torrentfile)
        resp.headers['Content-Type'] = 'application/x-bittorrent'
        resp.headers['Content-Disposition'] = 'attachment; filename=' + fn
        return resp

    else:
        abort(404)


@blueprint.route('/feed/', defaults={'category_id': 0})
@blueprint.route('/feed/<int:category_id>')
def feed(category_id=0):
    feed_data = get_feed_data(category_id)
    content = render_template(
        'feed.xml',
        channel=feed_data['channel'],
        items=feed_data['items']
    ).encode('utf-8')
    response = make_response(content)
    response.headers['content-type'] = 'application/rss+xml; charset=UTF-8'
    return response


@blueprint.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(blueprint.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@blueprint.route('/ping')
def ping():
    return "Alive: {}".format(datetime.datetime.utcnow().isoformat())


@blueprint.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html', env=os.environ)

