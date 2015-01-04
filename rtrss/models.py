import logging
from sqlalchemy import Column, Integer, String, ForeignKey, PickleType,\
    Boolean, BigInteger, DateTime
from sqlalchemy.orm import relationship, backref, relation
from sqlalchemy.ext.declarative import declarative_base

_logger = logging.getLogger(__name__)

Base = declarative_base()


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    title = Column(String(500), nullable=False)
    is_toplevel = Column(Boolean, nullable=False, default=False)
    has_torrents = Column(Boolean, nullable=False, default=False)

    # parent = relationship("Category", backref=backref('subcategories'))
    parent = relation('Category', remote_side=[id])

    def __repr__(self):
        return u"<Category(id={}, title='{}')>".format(self.id, self.title)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    password = Column(String(20), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    downloads_limit = Column(Integer, default=100)
    downloads_today = Column(Integer, nullable=False, default=0)
    cookies = Column(PickleType, default=dict())

    def __repr__(self):
        return u"<User(id={}, username='{}')>".format(self.id, self.username)


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    title = Column(String(500), nullable=False)
    created = Column(DateTime, nullable=False)
    category = relationship("Category", backref=backref('topics'))

    def __repr__(self):
        return u"<Topic(id={}, title='{}')>".format(self.id, self.title)
# TODO
# Index('idx_category_created', Topic.category_id, Torrent.created.desc())


class Torrent(Base):
    __tablename__ = 'torrents'
    infohash = Column(String(40), primary_key=True)
    tid = Column(Integer, ForeignKey('topics.id'))
    size = Column(BigInteger, nullable=False)
    tfsize = Column(Integer, nullable=False)  # torrent file size
    created = Column(DateTime, nullable=False)  # TODO

    topic = relationship('Topic', uselist=False)

    def __repr__(self):
        return u"<Torrent(tid={}, hash='{}')>".format(self.tid, self.infohash)
# TODO
# Index('idx_category_created', Torrent.category_id, Torrent.created.desc())
