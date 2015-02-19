# -*- coding: utf-8 -*-
import os
import datetime
import json
import random
from functools import wraps

from flask import (send_from_directory, render_template, make_response, abort,
                   Response, request, blueprints, )

from rtrss import config
from rtrss.storage import make_storage
from rtrss.webapphelpers import (make_category_tree, get_feed_data,
                                 check_auth)
from rtrss.caching import DiskCache
from rtrss import torrentfile


storage = make_storage(config.FILESTORAGE_SETTINGS, config.DATA_DIR)

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
    return render_template('index.html')


@blueprint.route('/loadtree')
def loadtree():
    # TODO replace DIskCache
    cache = DiskCache(os.path.join(config.DATA_DIR, 'cache'))
    cache_key = 'category_tree.json'

    if cache_key not in cache:
        tree = make_category_tree()
        jsontree = json.dumps(tree, ensure_ascii=False, separators=(',', ':'))
        jsondata = u"var treeData = {};".format(jsontree)
        cache[cache_key] = jsondata.encode('utf-8')
    dirname, filename = os.path.split(cache.full_path(cache_key))
    return send_from_directory(dirname, filename)


@blueprint.route('/torrent/<int:torrent_id>')
def torrent(torrent_id):
    passkey = request.args.get('pk')
    bindata = storage.get('{}.torrent'.format(torrent_id))

    if not bindata:
        abort(404)

    tf = torrentfile.TorrentFile(bindata)
    if passkey:
        ann_url = random.choice(config.ANNOUNCE_URLS)
        tf.add_announcer(ann_url + '?uk={}'.format(passkey))

    fn = '{}.torrent'.format(torrent_id)
    resp = make_response(tf.encoded)
    resp.headers['Content-Type'] = 'application/x-bittorrent'
    resp.headers['Content-Disposition'] = 'attachment; filename=' + fn
    return resp


@blueprint.route('/feed/', defaults={'category_id': 0})
@blueprint.route('/feed/<int:category_id>')
def feed(category_id=0):
    passkey = request.args.get('pk')
    feed_data = get_feed_data(category_id)
    content = render_template(
        'feed.xml',
        channel=feed_data['channel'],
        items=feed_data['items'],
        passkey=passkey
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


@blueprint.context_processor
def inject_auth():
    auth = request.authorization
    authorized = auth and check_auth(auth.username, auth.password)
    return dict(authorized=authorized)


@blueprint.route('/faq.html')
def faq():
    return render_template('faq.html')
