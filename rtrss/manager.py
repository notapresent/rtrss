"""
All database interactions are performed by Manager

"""
import logging
# from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound
from rtrss.scraper import Scraper
from rtrss.models import Topic, User, Category, Torrent
from rtrss.exceptions import TopicException, OperationInterruptedException
from rtrss.fstorage import make_storage

# Minimum and maximum number of torrents to store, per category
KEEP_TORRENTS_MIN = 25
KEEP_TORRENTS_MAX = 75

_logger = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, config, dbsession):
        self._storage = None
        self.config = config
        self.db = dbsession
        self.changed_categories = set()

    def update(self):
        _logger.debug('Starting update')
        torrents_added = 0
        user = self.select_user()

        updlist = self.make_update_list()

        for id, topic in updlist.items():
            try:
                torrents_added += self.process_topic(id, topic, user)
            except TopicException:
                pass
            self.db.commit()
            if not user.can_download:
                _logger.info('User %s reached download limit, changing', user)
                user = self.select_user()

        _logger.info('%d torrents added', torrents_added)

        self.invalidate_cache()

    def make_update_list(self):
        scraper = Scraper(self.config)
        latest = scraper.get_latest_topics()
        existing = self.load_topics(latest.keys())
        return self.new_topics(latest, existing)

    def cleanup(self):
        removed = 0
        # TODO
        _logger.info('Cleanup finished, %d torrents removed', removed)

    def daily_reset(self):
        '''Reset user download counters'''
        self.db.query(User).update({User.downloads_today: 0})
        _logger.info('Daily reset finished')

    def load_topics(self, ids):
        '''
        Loads existing topics from database, returns dict(topic_id: infohash)
        '''
        existing = self.db.query(Topic)\
            .options(joinedload(Topic.torrent))\
            .filter(Topic.id.in_(ids))\
            .all()
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
        parsed = scraper.get_topic(id, user)

        title = tdict['title']
        dt = tdict['updated_at']
        old_infohash = tdict.get('old_infohash')
        catlist = parsed['categories']
        infohash = parsed['infohash']

        if tdict['new'] or (infohash and infohash != old_infohash):
            self.save_topic(id, title, catlist, dt)

        if not infohash:
            return 0

        # Torrent new or changed
        if tdict['new'] or old_infohash != infohash:
            self.save_torrent(id, user, infohash, old_infohash)
            return 1

        return 0

    def save_topic(self, id, title, categories, updated_at):
        '''
        Insert or update topic and categories
        '''
        topic = self.db.query(Topic).get(id)

        if categories:
            category = categories.pop()
            self.ensure_category(category, categories)
        else:
            category = None
            action = 'Updating' if topic else 'Adding'
            _logger.warn('%s topic without category: %d', action, id)

        if topic:
            if category:
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

    def save_torrent(self, id, user, infohash, old_infohash=None):
        # FIXME this method needs refactoring
        # Increment download counter, download, decrement it if error
        scraper = Scraper(self.config)
        torrentfile = scraper.get_torrent(id, user)
        user.downloads_today += 1

        parsed = scraper.parse_torrent(torrentfile)

        if infohash.lower() != parsed['infohash'].lower():
            msg = 'Torrent {} hash mismatch: {}/{}'.format(id, infohash,
                                                           parsed['infohash'])
            _logger.error(msg)
            raise TopicException(msg)

        t = self.db.query(Torrent).get(id)

        # TODO find duplicates by infohash

        if t:
            t.infohash = infohash
            t.tfsize = len(torrentfile)
            t.size = parsed['size']
        else:
            t = Torrent(
                id=id,
                infohash=infohash,
                size=parsed['size'],
                tfsize=len(torrentfile)
            )

        self.db.add(t)
        self.store_torrentfile(id, torrentfile)

    @property
    def storage(self):
        if self._storage:
            return self._storage
        else:
            self._storage = make_storage(self.config)
            return self._storage

    def store_torrentfile(self, id, torrentfile):
        # TODO add mimetype
        self.storage.put('{}.torrent'.format(id), torrentfile)

    def invalidate_cache(self):
        for cid in self.changed_categories:
            self.changed_categories.remove(cid)
            # TODO do actual invalidation here

    def select_user(self):
        '''Select one random user with download slots available'''
        try:
            user = self.db.query(User)\
                .filter(User.enabled.is_(True))\
                .filter(User.downloads_limit > User.downloads_today)\
                .order_by(func.random()).limit(1).one()
        except NoResultFound:
            raise OperationInterruptedException('No active users found')

        self.db.add(user)
        return user

    def import_categories(self):
        '''Import all existing tracker categories into DB'''
        _logger.info('Importing all categories from tracker')
        old = new = 0
        user = self.select_user()
        scraper = Scraper(self.config)

        for id in scraper.get_category_ids(user):
            c = self.db.query(Category).get(id)

            if c:
                old += 1
                continue

            catlist = scraper.get_forum_categories(id, user)

            if not catlist:
                _logger.warn('Unable to get category list for forum %d', id)
                continue

            self.ensure_category(catlist.pop(), catlist)
            new += 1
            self.db.commit()

        _logger.info("Category import completed, %d old, %d new", old, new)

    def populate_categories(self, count=1, total=None):
        """
        Add count (or less) torrents to every category with less then count
        torrents, no more than total torrents
        """
        categories = self.db.query(Category, func.count(Torrent.id))\
            .outerjoin(Topic)\
            .outerjoin(Torrent)\
            .filter(Category.is_subforum)\
            .filter(Category.skip.isnot(True))\
            .group_by(Category.id)\
            .having(func.count(Torrent.id) < count)\
            .order_by(Category.id)\
            .all()

        _logger.debug(
            'Found %d categories with less than %d torrents',
            len(categories),
            count
        )

        if not len(categories):
            return

        if total is None:
            if count == 1:
                total = len(categories)
            else:
                raise ValueError('total parameter is required if count > 1')

        total_added = 0

        for cat, ntorrents in categories:
            # If this category has some torrents - only add missing amount
            to_add = count if ntorrents == count else count - ntorrents

            # Do not add more than total
            if total_added + to_add > total:
                to_add = total - total_added

            num_added = self.populate_category(cat.id, to_add)
            total_added += num_added
            if not num_added:
                cat.skip = True
            self.db.commit()

            if total_added == total:
                break

        _logger.info(
            'Added %d torrents to %d categories',
            total_added,
            len(categories)
        )

    def populate_category(self, category_id, count):
        """Add count torrents from category category_id"""
        scraper = Scraper(self.config)
        user = self.select_user()
        torrents = scraper.find_torrents(user, category_id)

        added = 0

        if not torrents:
            _logger.debug('No torrents found in category %d', category_id)
            return 0

        for tdict in torrents:
            exists = self.db.query(Topic).get(tdict['id'])

            # Skip torrents that are already in database
            if exists:
                continue

            tdict['new'] = True
            try:
                added += self.process_topic(tdict['id'], tdict, user)
            except TopicException:
                _logger.debug('Failed to add topic %d', tdict['id'])

            if not user.can_download():
                user = self.select_user()

            if added == count:
                break

        return added
