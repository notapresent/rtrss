# -*- coding: utf-8 -*-
import os
import datetime
import rfc822
from functools import wraps

from flask import (Flask, send_from_directory, render_template, make_response,
                   abort, Response, request)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import orm, func

from rtrss.models import Topic, Category, Torrent
from rtrss.filestorage import make_storage
from rtrss import config


app = Flask(__name__)
app.config.from_object('rtrss.config')
db = SQLAlchemy(app)

MIN_TTL = 30  # minutes
MAX_TTL = 1440  # 1 day


@app.route('/')
def index():
    tree = make_category_tree()
    return render_template('index.html', tree=tree)


@app.route('/torrent/<int:torrent_id>')
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


@app.route('/feed/', defaults={'category_id': 0})
@app.route('/feed/<int:category_id>')
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


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/ping')
def ping():
    return "Alive: {}".format(datetime.datetime.utcnow().isoformat())


@app.before_first_request
def setup():
    pass  # TODO cache warmup etc


def check_auth(username, password):
    """
    This function is called to check if a username/password combination is valid
    """
    return (username == app.config['ADMIN_LOGIN']
            and password == app.config['ADMIN_PASSWORD'])


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


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html', env=os.environ)


def get_feed_data(category_id):
    category = db.session.query(Category).get(category_id)
    if category_id:
        description = u'Новые раздачи в разделе {}'.format(category.title)
    else:
        description = u'Новые раздачи из всех разделов'

    channel_data = dict({
        'title': u'{} - {}'.format(app.config['TRACKER_HOST'], category.title),
        'description': description,
        'link': category_link(category, app.config['TRACKER_HOST']),
        'lastBuildDate': datetime_to_rfc822(datetime.datetime.utcnow())
    })

    category_ids = get_subcategories([category_id]) if category_id else None
    topics = get_feed_items(category_ids)

    if not topics:
        raise RuntimeError('This feed is empty')

    items = list()
    deltas = list()
    last_dt = None

    for topic in topics:
        items.append(dict({
            'id': topic.id,
            'title': topic.title,
            'guid': topic.torrent.infohash,
            'pubDate': datetime_to_rfc822(topic.updated_at),
        }))

        if last_dt:
            delta = last_dt - topic.updated_at
            deltas.append(delta.total_seconds())

        last_dt = topic.updated_at

    channel_data['ttl'] = int(calculate_ttl(deltas) / 60)
    return dict({'channel': channel_data, 'items': items})


def calculate_ttl(deltas):
    """
    Calculations are based on median time delta between items and the number of
    items. Accepts a list if time deltas.
    """

    # Feed with only 1 item
    if len(deltas) == 0:
        return MAX_TTL

    def median(lst):
        lst.sort()
        length = len(lst)
        middle = length / 2
        if length % 2:
            return lst[middle]
        else:
            return (lst[middle - 1] + lst[middle]) / 2.0

    median_delta = median(deltas)
    ttl = median_delta * (len(deltas) + 1) / 2
    ttl = min(max(ttl, MIN_TTL), MAX_TTL)  # Ensure MIN_TTL <= ttl <= MAX_TTL
    return ttl


def datetime_to_rfc822(the_time):
    parsed = rfc822.parsedate_tz(the_time.strftime("%a, %d %b %Y %H:%M:%S"))
    return rfc822.formatdate(rfc822.mktime_tz(parsed))


def get_subcategories(parent_ids):
    """Returns list of all subcategory ids"""
    subcategories = db.session.query(Category.id) \
        .filter(Category.parent_id.in_(parent_ids)) \
        .all()

    children = [cat_id for (cat_id, ) in subcategories]

    if children:
        children += get_subcategories(children)

    return parent_ids + children


def get_feed_items(category_ids=None):
    if category_ids is None or len(category_ids) > 1:
        limit = 75
    else:
        limit = 25

    query = db.session.query(Topic).join(Torrent)

    if category_ids:
        query = query.filter(Topic.category_id.in_(category_ids))

    return query.order_by(Topic.updated_at.desc()).limit(limit).all()


def category_link(category, tracker_host):
    if category.is_subforum:
        return "http://{host}/forum/viewforum.php?f={cid}".format(
            host=tracker_host, cid=category.tracker_id)
    else:
        return "http://{host}/forum/index.php?c={cid}".format(
            host=tracker_host, cid=category.tracker_id)


def make_category_tree():
    categories = category_list()

    tree = dict({
        'id': 0,
        'title': 'Root',
        'parent_id': None,
        'children': list()
    })
    childmap = dict({0: tree['children']})

    for category in categories:
        catdict = dict({
            'id': category.id,
            'title': category.title,
            'parent_id': category.parent_id,
            'children': list()
        })

        childmap[category.id] = catdict['children']
        childmap[category.parent_id].append(catdict)

    return tree


def category_list(return_empty=False):
    """Returns category list with torrent count for each category"""
    q = db.session
    top = (
        orm.query.Query(
            [Category.id.label('root_id'), Category.id.label('id')]
        )
        .cte('descendants', recursive=True)
    )

    descendants = (
        top.union_all(
            orm.query.Query([top.c.root_id, Category.id])
            .filter(Category.parent_id == top.c.id))
    )

    tc = (
        q.query(Topic.category_id, Torrent.id)
        .join(Torrent, Torrent.id == Topic.id)
        .subquery(name='tc')
    )

    tcc = (
        q.query(descendants.c.root_id, func.count(tc.c.id).label('cnt'))
        .filter(descendants.c.id == tc.c.category_id)
        .group_by(descendants.c.root_id)
        .subquery(name='tcc')
    )

    outer = (
        q.query(Category.id, Category.parent_id, Category.title, tcc.c.cnt)
        .outerjoin(tcc, tcc.c.root_id == Category.id)
        .filter(Category.id > 0)
        .order_by(Category.is_subforum)
        .order_by(Category.parent_id)
        .order_by(Category.tracker_id)
    )

    if not return_empty:
        outer = outer.filter(tcc.c.cnt > 0)

    return outer.all()
