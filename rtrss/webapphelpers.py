# -*- coding: utf-8 -*-
import datetime
import rfc822

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import orm, func

from rtrss.models import Topic, Category, Torrent
from rtrss import config


MIN_TTL = 30  # minutes
MAX_TTL = 1440  # 1 day

db = SQLAlchemy()


def check_auth(login, password):
    """
    This function is called to check if a username/password combination is valid
    """
    return login == config.ADMIN_LOGIN and password == config.ADMIN_PASSWORD


def get_feed_data(category_id):
    category = db.session.query(Category).get(category_id)
    if category_id:
        description = u'Новые раздачи в разделе {}'.format(category.title)
    else:
        description = u'Новые раздачи из всех разделов'

    channel_data = dict({
        'title': u'{} - {}'.format(config.TRACKER_HOST, category.title),
        'description': description,
        'link': category_link(category, config.TRACKER_HOST),
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
    if category_ids is None:  # Root category
        limit = 100
    elif len(category_ids) > 1:  # Category with subcategories
        limit = 75
    else:  # Leaf category
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

    tree = [dict({
        'fid': 0,
        'text': u'Все разделы',
        'parent_fid': None,
        # 'nodes': list()
    })]
    childmap = dict({0: tree[0]})

    for category in categories:
        catdict = dict({
            'fid': category.id,
            'text': category.title,
            # 'parent_fid': category.parent_id,
        })

        childmap[category.id] = catdict

        if 'nodes' not in childmap[category.parent_id]:
            childmap[category.parent_id]['nodes'] = list()

        childmap[category.parent_id]['nodes'].append(catdict)

    sort_leafs_first(tree)
    return tree


def sort_leafs_first(tree):
    tree.sort(key=lambda n: 0 if 'nodes' in n else 1)

    for item in tree:
        if 'nodes' in item:
            sort_leafs_first(item['nodes'])


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
