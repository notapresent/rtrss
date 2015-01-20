# -*- coding: utf-8 -*-
import os
import datetime
import rfc822
from flask import Flask, send_from_directory, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from rtrss.models import Topic, User, Category, Torrent
from rtrss.filestorage import make_storage

app = Flask(__name__)
app.config.from_object('rtrss.config')
db = SQLAlchemy(app)

MIN_TTL = 30    # minutes
MAX_TTL = 1440  # 1 day

@app.route('/')
def index():
    tree = make_category_tree()
    return render_template('index.html', tree=tree)


@app.route('/torrent/<int:torrent_id>')
def torrent(torrent_id):
    pass

# @app.route('/feed/', defaults={'category_id': 0})     
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

@app.before_first_request
def setup():
    pass    # TODO cache warmup etc


def get_feed_data(category_id):
    category = db.session.query(Category).get(category_id)
    channel_data = dict({
        'title': category.title,
        'description': u'Новые раздачи в разделе {}'.format(category.title),
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

    ttl = min(max(ttl, MIN_TTL), MAX_TTL)   # Ensure MIN_TTL <= ttl <= MAX_TTL
    print "Median delta:", median_delta, "Length:", len(deltas) + 1, ' TTL:', str(ttl)
    return ttl

def datetime_to_rfc822(the_time):
    parsed = rfc822.parsedate_tz(the_time.strftime("%a, %d %b %Y %H:%M:%S"))
    return rfc822.formatdate(rfc822.mktime_tz(parsed))


def get_subcategories(parent_ids):
    """Returns list of all subcategory ids"""
    subcategories = db.session.query(Category.id)\
        .filter(Category.parent_id.in_(parent_ids))\
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

    query = db.session.query(Topic)\
        .join(Torrent)\


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
    # TODO show only categories with torrents
    categories = (
        db.session.query(Category)
            .filter(Category.id > 0)
            .order_by(Category.is_subforum)
            .order_by(Category.parent_id)
            .order_by(Category.tracker_id)
            .all()
    )

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

if __name__ == '__main__':
    app.run(app.config['IP'], app.config['PORT'], debug=True)
