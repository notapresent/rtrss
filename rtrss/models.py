import logging
from sqlalchemy import Column, Integer, String, ForeignKey, PickleType,\
    Boolean, BigInteger, DateTime, Index
from sqlalchemy.orm import relationship, relation
from sqlalchemy.ext.declarative import declarative_base


__all__ = ["Category", "Topic", "Torrent", "User"]

_logger = logging.getLogger(__name__)

Base = declarative_base()


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=False)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    title = Column(String(500), nullable=False)
    is_subforum = Column(Boolean, nullable=False, default=True)
    # Skip this category during initial categories population
    skip = Column(Boolean, nullable=True)

    parent = relation('Category', remote_side=[id])

    def __repr__(self):
        return u"<Category(id={}, title='{}')>".format(self.id, self.title)


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True, autoincrement=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    title = Column(String(500), nullable=False)
    # 'Updated' value provided by the tracker, UTC
    updated_at = Column(DateTime, nullable=False)

    category = relationship("Category", backref='topics')
    torrent = relationship('Torrent', uselist=False, backref='topic')

    def __repr__(self):
        return u"<Topic(id={}, title='{}')>".format(self.id, self.title)

# TODO Tune
# Index('ix_category_updated_at', Topic.category_id, Torrent.updated_at.desc())
Index('ix_category', Topic.category_id)
Index('ix_updated_at', Topic.updated_at.desc())


class Torrent(Base):
    __tablename__ = 'torrents'

    id = Column(Integer, ForeignKey('topics.id'), primary_key=True, autoincrement=False)
    infohash = Column(String(40), index=True, unique=True)
    size = Column(BigInteger, nullable=False)
    tfsize = Column(Integer, nullable=False)  # torrent file size

    # topic = relationship('Topic', uselist=False)

    def __repr__(self):
        return u"<Torrent(id={}, hash='{}')>".format(self.id, self.infohash)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=False)
    username = Column(String(50), nullable=False)
    password = Column(String(20), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    downloads_limit = Column(Integer, default=100)
    downloads_today = Column(Integer, nullable=False, default=0)
    cookies = Column(PickleType, default=dict())

    def can_download(self):
        """Returns True if user can download torrent files"""
        if not self.enabled:
            return False
        if (self.downloads_limit and
                self.downloads_today < self.downloads_limit):
            return False
        return True

    def __repr__(self):
        return u"<User(id={}, username='{}')>".format(self.id, self.username)
