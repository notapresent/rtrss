"""
All database interactions are performed by Manager

"""
import logging
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound
from .scraper import Scraper
from .models import Topic, User, Category, Torrent
from . import TopicException, OperationInterruptedException

# Per category
KEEP_TORRENTS = 50

_logger = logging.getLogger(__name__)



class Manager(object):
    def __init__(self, config, dbsession):
        self.config = config
        self.db = dbsession
        self.changed_categories = set()

    def update(self):
        _logger.debug('Starting update')
        scraper = Scraper(self.config)

        latest = scraper.get_latest_topics()
        existing = self.load_topics(latest.keys())
        new = self.new_topics(latest, existing)

        user = self.select_user()
        torrents_added = 0

        for id, topic in new.items():
            try:
                torrents_added += self.process_topic(id, topic, user)
                self.db.commit()
            except TopicException as e:
                pass



        if torrents_added:
            _logger.info('%d torrents added', torrents_added)
        else:
            _logger.debug('No torrents added')

        self.invalidate_cache()

    def cleanup(self):
        _logger.info('Cleanup')

    def daily_reset(self):
        _logger.info('Daily reset')

    def load_topics(self, ids):
        '''
        Loads existing topics from database, returns dict(topic_id: infohash)
        '''
        existing = self.db.query(Topic).options(joinedload(Topic.torrent)).\
            filter(Topic.id.in_(ids)).all()
        result = dict()
        for t in existing:
            result[t.id] = t.torrent.infohash if t.torrent else None

        return result

    def new_topics(self, latest, existing):
        existing_ids = existing.keys()
        result = dict()

        for id, topic in latest.items():
            # new topic
            if id not in existing_ids:
                result[id] = topic
                result[id]['new'] = True

            # updated existing topic
            elif topic['changed']:
                result[id] = topic
                result[id]['new'] = False
                result[id]['old_infohash'] = existing[id]


        return result

    def process_topic(self, id, tdict, user):
        '''
        Process topic, categories and torrent. Returns 1 if torrent was added
        or updated, 0 otherwise
        '''
        scraper = Scraper(self.config)
        parsed = scraper.load_topic(id, user)

        title = tdict['title']
        dt = tdict['updated_at']
        catlist = parsed['categories']
        infohash = parsed['infohash']
        old_infohash = tdict.get('old_infohash')

        if tdict['new'] or (infohash and infohash != old_infohash):
            self.save_topic(id, title, catlist, dt)

        if not infohash:
            return 0

        if tdict['new'] or old_infohash != infohash:
            self.save_torrent(id, infohash, old_infohash)
            return 1

        return 0

    def save_topic(self, id, title, categories, updated_at):
        '''
        Insert or update topic and categories
        '''
        if categories:
            category = categories.pop()
            self.ensure_category(category, categories)
        else:
            category = None

        topic = self.db.query(Topic).get(id)

        if topic:
            topic.category_id = category['id']
            topic.title = title
            topic.updated_at = updated_at

        else:
            topic = Topic(
                id=id,
                category_id=category['id'] if category else None,
                title=title,
                updated_at=updated_at
            )

        _logger.debug('Saving topic %s', topic)
        self.db.add(topic)
        return topic

    def ensure_category(self, cat, parents):
        '''
        Check if category exists, create if not. Create all parent
        categories if needed.
        '''
        category = self.db.query(Category).get(cat['id'])

        if category:
            return

        if parents:
            parent_cat = parents.pop()
            parent = self.db.query(Category).get(parent_cat['id'])

            if not parent:
                self.ensure_category(parent_cat, parents)

        category = Category(
            id=cat['id'],
            title=cat['title'],
            parent_id=cat['parent_id'],
            is_subforum=cat['is_subforum']
        )

        _logger.info('Adding category %s', category)
        self.db.add(category)

    def save_torrent(self, id, infohash, old_infohash=None):
        t = self.db.query(Torrent).get(id)
        if t:
            t.infohash = infohash
            t.tfsize = 0
            t.size = 0
        else:
            t = Torrent(
                tid=id,
                infohash=infohash,
                size=0,
                tfsize=0
            )

        self.db.add(t)

    def invalidate_cache(self):
        for cid in self.changed_categories:
            self.changed_categories.remove(cid)
            # TODO do actual invalidation here


    def select_user(self):
        '''Select one random user with download slots available'''
        try:
            user = self.db.query(User).\
                filter(User.enabled.is_(True)).\
                filter(User.downloads_limit > User.downloads_today).\
                order_by(func.random()).limit(1).one()
        except NoResultFound as e:
            raise OperationInterruptedException('No active users found')

        return user


if __name__ == '__main__':
    from . import config
    from database import Session
    import sys

    logging.basicConfig(
        level=config.LOGLEVEL, stream=sys.stdout,
        format='%(asctime)s %(levelname)s %(name)s %(message)s')

    # Limit 3rd-party packages logging
    logging.getLogger('schedule').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    m = Manager(config, Session())
    m.update()
