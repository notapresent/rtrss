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
        topics = self.load_topics(scraper.get_latest_topics())

        for topic in topics:
            self.process_topic(topic)
            self.db.commit()

        self.invalidate_cache()

    def cleanup(self):
        _logger.info('Cleanup')

    def daily_reset(self):
        _logger.info('Daily reset')

    def load_topics(self, latest):
        '''Returns list of dicts'''
        existing = self.db.query(Topic).\
            filter(Topic.id.in_([t['id'] for t in latest])).\
            all()
        return []

    def process_topic(self, topic):
        pass

    def invalidate_cache(self):
        pass


if __name__ == '__main__':
    from . import config
    from worker import Session
    m = Manager(config, Session())
    m.update()
