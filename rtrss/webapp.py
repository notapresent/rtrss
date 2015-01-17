# -*- coding: utf-8 -*-
import os
import datetime
import rfc822
from flask import Flask, send_from_directory, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from rtrss.models import Topic, User, Category, Torrent

app = Flask(__name__)
app.config.from_object('rtrss.config')
db = SQLAlchemy(app)

# print app.config['SERVER_NAME']; import sys; sys.exit()

@app.route('/')
def index():
    tree = make_category_tree()
    return render_template('index.html', tree=tree)


@app.route('/torrent/<int:torrent_id>')
def torrent(torrent_id):
    pass

@app.route('/feed/')
def feed():
    feed_data = get_feed_data()
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
    pass
    # Recreate database each time for demo
    # Base.metadata.drop_all(bind=db.engine)
    # Base.metadata.create_all(bind=db.engine)


def get_feed_data(category_id=0):
    category = db.session.query(Category).get(category_id)
    channel_data = dict({
        'title': category.title,
        'description': u'Новые раздачи в разделе {}'.format(category.title),
        'link': category_link(category, app.config['TRACKER_HOST']),
        'lastBuildDate': datetime_to_rfc822(datetime.datetime.utcnow())
    })

    category_ids = get_subcategories([category_id]) if category_id else None
    topics = get_feed_items(category_ids)

    items = list()
    for topic in topics:
        items.append(dict({
            'id': topic.id,
            'title': topic.title,
            'guid': topic.torrent.infohash,
            'pubDate': datetime_to_rfc822(topic.updated_at)
        }))
    # TODO: TTL
    return dict({'channel': channel_data, 'items': items})


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
        .order_by(Topic.updated_at.desc())\
        .limit(limit)

    if category_ids:
        query = query.filter(Topic.category_id.in_(category_ids))

    return query.all()


def category_link(category, tracker_host):
    if category.is_subforum:
        return "http://{host}/forum/index.php?c={cid}".format(
            host=tracker_host, cid=category.id)
    else:
        return "http://{host}/forum/viewforum.php?f={cid}".format(
            host=tracker_host, cid=category.id)


def make_category_tree():
    categories = db.session.query(Category)\
        .filter(Category.skip.isnot(True))\
        .order_by(Category.parent_id)\
        .order_by(Category.id)\
        .all()

    tree = dict()
    for cat in categories:
        if not cat.parent_id:
            tree[cat.id] = cat
            continue

        if cat.parent_id in tree:
            parent = tree[cat.parent_id]

            if not parent.get('children'):
                parent['children'] = list()

            parent['children'].append(cat)

        else:
            raise IndexError("Parent for {} not found".format(cat.id))


if __name__ == '__main__':
    app.run('0.0.0.0', 8080, debug=True)
