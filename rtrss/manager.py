"""
All database interactions are performed by Manager

"""
import logging
from sqlalchemy import or_
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound
from .scraper import Scraper
from .models import Topic, User, Category, Torrent
from . import TopicException
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

        for id, topic in new.items():
            try:
                self.process_topic(id, topic)
                self.db.commit()
            except TopicException as e:
                pass

        # self.invalidate_cache()

    def cleanup(self):
        _logger.info('Cleanup')

    def daily_reset(self):
        _logger.info('Daily reset')

    def load_topics(self, ids):
        '''
        Loads existing topics from database, returns dict(topic_id: infohash)
        '''
        existing = self.db.query(Topic).filter(Topic.id.in_(ids)).all()
        return {t.id: t.torrent.infohash for t in existing}

    def new_topics(self, latest, existing):
        existing_ids = existing.keys()
        result = dict()

        for id, topic in latest.items():
            # new topic
            if id not in existing_ids:
                result[id] = topic

            # updated existing topic
            elif topic['torrent_updated']:
                result[id] = topic
                result[id]['old_infohash'] = existing[id]

        return result

    def process_topic(self, id, topic_dict):
        user = self.select_user()
        scraper = Scraper(self.config)
        parsed = scraper.load_topic(id, user)

        t = Topic(
            id=id,
            category_id: None
            title=topic_dict['title'],
            created=topic_dict['updated_at']
        )

        self.db.add(t)

        if not parsed:
            if topic['torrent_updated']:
                _logger.warn('Topic updated but no torrent found: %s', t)
            return 0

        for cat in parsed['categories']:
            self.ensure_category(cat)

        print topic.keys(), parsed.keys()


    def ensure_category(self, cat):
        '''Check if category exists, create if not'''
        category = self.db.query(Category).get(cat['id'])

        if category:
            return

        category = Category(
            id=cat['id'],
            title=cat['title'],
            parent_id=cat['parent_id'],
            is_toplevel=cat['is_toplevel'],
            has_torrents=cat['has_torrents']
        )

        _logger.info('Adding category %s', category)

        self.db.add(category)

    def invalidate_cache(self):
        for cid in self.changed_catedories:
            self.changed_categories.remove(cid)
            # TODO do actual invalidation here


    def select_user(self):
        try:
            user = self.db.query(User).\
                filter(User.enabled.is_(True)).\
                filter(or_(
                    User.downloads_limit.is_(None),
                    User.downloads_limit > User.downloads_today
                    )).\
                order_by(func.random()).\
                limit(1).one()
        except NoResultFound as e:
            raise OperationInterruptedException('No active users found')
        else:
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
