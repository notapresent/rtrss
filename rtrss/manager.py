"""
All database interactions are performed by Manager

"""
import logging
from .scraper import Scraper
from .models import Topic

_logger = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, config, dbsession):
        self.config = config
        self.db = dbsession

    def update(self):
        _logger.debug('Starting update')
        scraper = Scraper(self.config)

        latest = scraper.get_latest_topics()
        existing = self.load_topics(latest.keys())
        new = self.new_topics(latest, existing)

        for id, topic in new.items():
            self.process_topic(id, topic)

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

    def process_topic(self, id, topic):
        pass

    def invalidate_cache(self):
        pass


if __name__ == '__main__':
    from . import config
    from worker import Session
    m = Manager(config, Session())
    m.update()
