import os

from flask import (Flask, render_template)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import orm, func

from rtrss.models import *


app = Flask(__name__)
# app.config.from_object('rtrss.config')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'OPENSHIFT_POSTGRESQL_DB_URL',
    'postgresql://postgres:postgres@localhost/rtrss_dev')
db = SQLAlchemy(app)


@app.route('/')
def index():
    tree = make_category_tree()
    return render_template('index.html', tree=tree)


@app.route('/feed/', defaults={'category_id': 0})
@app.route('/feed/<int:category_id>')
def feed(category_id=0):
    pass


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

