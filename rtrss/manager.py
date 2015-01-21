# -*- coding: utf-8 -*-
"""
All database interactions are performed by Manager

"""
import logging
import datetime

from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound

from rtrss.scraper import Scraper
from rtrss.models import Topic, User, Category, Torrent
from rtrss.exceptions import (TopicException, OperationInterruptedException,
                              CaptchaRequiredException, TorrentFileException,
                              ItemProcessingFailedException)
from rtrss.filestorage import make_storage


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

            except (CaptchaRequiredException, TorrentFileException):
                user.downloads_today = user.downloads_limit
                self.db.add(user)
                _logger.debug('User %s - torrent dl failed', user)

            if not user.can_download():
                _logger.info('User %s reached download limit, changing', user)
                user.downloads_today = user.downloads_limit
                user = self.select_user()

            self.db.commit()

        _logger.info('%d torrents added', torrents_added)

        self.invalidate_cache()

    def make_update_list(self):
        scraper = Scraper(self.config)
        latest = scraper.get_latest_topics()
        existing = self.load_topics(latest.keys())
        return self.new_topics(latest, existing)

    def cleanup(self):
        removed = 0
        # TODO Implement this
        _logger.info('Cleanup finished, %d torrents removed', removed)

    def daily_reset(self):
        """Reset user download counters"""
        self.db.query(User).update({User.downloads_today: 0})
        _logger.info('Daily reset finished')

    def load_topics(self, ids):
        """
        Loads existing topics from database, returns dict(topic_id: infohash)
        """
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
        """
        Process topic, categories and torrent. Returns 1 if torrent was added
        or updated, 0 otherwise
        """
        scraper = Scraper(self.config)
        parsed = scraper.get_topic(id, user)

        title = tdict['title']
        dt = tdict['updated_at']
        old_infohash = tdict.get('old_infohash')
        catlist = parsed['categories']
        infohash = parsed['infohash']

        # Save topic only if it is new or infohash changed (but not removed)
        if tdict['new'] or (infohash and infohash != old_infohash):
            self.save_topic(id, title, catlist, dt)
            result = 1
        else:
            result = 0

        # do not save torrent if no infohash
        if not infohash:
            return result

        # Torrent new or changed
        if tdict['new'] or old_infohash != infohash:
            self.save_torrent(id, user, infohash, old_infohash)

        return result

    def save_topic(self, id, title, categories, updated_at):
        """
        Insert or update topic and categories
        """
        topic = self.db.query(Topic).get(id)


        category = categories.pop()
        category_id = self.ensure_category(category, categories)

        if topic:
            topic.category_id = category_id
            topic.title = title
            topic.updated_at = updated_at

        else:
            topic = Topic(
                id=id,
                category_id=category_id,
                title=title,
                updated_at=updated_at
            )

        _logger.debug('Saving topic %s', topic)
        self.db.add(topic)
        return topic

    def ensure_category(self, cat, parents):
        """
        Check if category exists, create if not. Create all parent
        categories if needed. Returns category id
        """
        category = (
            self.db.query(Category).filter(
                Category.tracker_id==cat['tracker_id'],
                Category.is_subforum==cat['is_subforum']
            ).first()
        )

        if category:
            return category.id

        if parents:
            parent_cat = parents.pop()
            parent = (
                self.db.query(Category).filter(
                    Category.tracker_id==parent_cat['tracker_id'],
                    Category.is_subforum==parent_cat['is_subforum']
                ).first()
            )

            if parent:
                parent_id = parent.id
            else:
                parent_id = self.ensure_category(parent_cat, parents)
        else:
            parent_id = None
            _logger.warn('No parent category for %s(%d)',
                cat['tracker_id'], cat['title'])

        category = Category(
            tracker_id=cat['tracker_id'],
            is_subforum=cat['is_subforum'],
            title=cat['title'],
            parent_id=parent_id,
            skip=cat.get('skip')
        )

        _logger.info('Adding category %s', category)
        self.db.add(category)
        self.db.flush()
        return category.id

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

        torrent = self.db.query(Torrent) \
            .filter(Torrent.infohash == infohash) \
            .first()

        if torrent:
            msg = 'Torrent with infohash {} already exists: {}'.format(
                infohash, torrent)
            _logger.error(msg)
            raise TopicException(msg)

        torrent = self.db.query(Torrent).get(id)

        if torrent:
            torrent.infohash = infohash
            torrent.tfsize = len(torrentfile)
            torrent.size = parsed['size']
        else:
            torrent = Torrent(
                id=id,
                infohash=infohash,
                size=parsed['size'],
                tfsize=len(torrentfile)
            )

        self.db.add(torrent)
        self.store_torrentfile(id, torrentfile)

    @property
    def storage(self):
        if self._storage:
            return self._storage
        else:
            self._storage = make_storage(self.config)
            return self._storage

    def store_torrentfile(self, id, torrentfile):
        filename = 'torrents/{}.torrent'.format(id)
        self.storage.put(
            filename,
            torrentfile,
            mimetype='application/x-bittorrent'
        )

    def invalidate_cache(self):
        pass  # TODO implement this

    def select_user(self):
        """Select one random user with download slots available"""
        try:
            user = self.db.query(User)\
                .filter(User.enabled.is_(True))\
                .filter(User.downloads_limit > User.downloads_today)\
                .order_by(func.random()).limit(1).one()
        except NoResultFound:
            self.db.commit()
            raise OperationInterruptedException('No active users found')

        return user

    def import_categories(self):
        """Import all existing tracker categories into DB"""
        _logger.info('Importing all categories from tracker')
        old = self.db.query(func.count(Category.id)).scalar()

        user = self.select_user()
        scraper = Scraper(self.config)

        root = self.db.query(Category).get(0)
        if not root:
            root = Category(
                id=0,
                title=u'Все разделы',
                parent_id=None,
                tracker_id=0,
                is_subforum=False,
                skip=True
            )
            self.db.add(root)

        for forum_id in scraper.get_forum_ids(user):
            category = (
                self.db.query(Category)
                .filter(
                    Category.tracker_id==forum_id,
                    Category.is_subforum==True
                )
                .first()
            )

            if category:
                continue
            try:
                catlist = scraper.get_forum_categories(forum_id, user)
            except ItemProcessingFailedException as e:
                _logger.error("Failed to import category: {}".format(e))

            if not catlist:
                _logger.warn('Unable to get category list for %d', forum_id)
                continue

            self.ensure_category(catlist.pop(), catlist)
            self.db.commit()

        new = self.db.query(func.count(Category.id)).scalar()
        _logger.info("Category import completed, %d old, %d new", old, new-old)

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
            to_add =  count - ntorrents

            # Do not add more than total
            if total_added + to_add > total:
                to_add = total - total_added

            num_added = self.populate_category(cat.tracker_id, to_add)
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
        try:
            torrents = scraper.find_torrents(user, category_id)
        except ItemProcessingFailedException as e:
            msg = "Failed to populate category {}: {}".format(category_id, e)
            _logger.error(msg)

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
                self.db.commit()
            except TopicException:
                _logger.debug('Failed to add topic %d', tdict['id'])

            if not user.can_download():
                user = self.select_user()

            if added == count:
                break

        return added

    def estimate_free_download_slots(self, days=7):
        """Calculates estimated download slots available based on number
        of torrents, downloaded each day during past week
        """
        today = datetime.datetime.utcnow().date()
        week = (datetime.datetime.utcnow() - datetime.timedelta(days)).date()
        num_downloads = self.db.query(func.count(Torrent.id)) \
            .join(Topic) \
            .filter(func.date(Topic.updated_at) >= week) \
            .filter(func.date(Topic.updated_at) < today) \
            .scalar()

        daily_slots = self.db.query(func.sum(User.downloads_limit)) \
            .filter(User.enabled) \
            .scalar()

        slots_left_today = self.db.query(
            func.sum(User.downloads_limit - User.downloads_today)) \
            .filter(User.enabled) \
            .scalar()

        estimate = daily_slots - (num_downloads / days)

        if estimate > slots_left_today:
            estimate = slots_left_today

        if estimate > 1000:
            estimate = 1000

        return int(estimate * 0.9)

    def daily_populate_task(self):
        dlslots = self.estimate_free_download_slots()
        _logger.info("Going to download %d torrents", dlslots)
        self.populate_categories(KEEP_TORRENTS_MIN, dlslots)
