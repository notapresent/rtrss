# -*- coding: utf-8 -*-
"""
All database interactions are performed by Manager
"""
import logging
import datetime
import os

from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from newrelic.agent import BackgroundTask

from rtrss.scraper import Scraper
from rtrss.models import Topic, User, Category, Torrent
from rtrss.exceptions import (TopicException, OperationInterruptedException,
                              CaptchaRequiredException, TorrentFileException,
                              ItemProcessingFailedException,
                              DownloadLimitException)
import rtrss.filestorage as filestorage
from rtrss.database import session_scope
from rtrss import util
from rtrss.caching import DiskCache



# Minimum and maximum number of torrents to store, per category
KEEP_TORRENTS_MIN = 25
KEEP_TORRENTS_MAX = 75

_logger = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, config):
        self._storage = None
        self.config = config
        self.changed_categories = set()

    @property
    def storage(self):
        if self._storage:
            return self._storage
        else:
            self._storage = filestorage.make_storage(self.config)
            return self._storage

    def run_task(self, task_name, *args, **kwargs):
        """Run task, catching all exceptions"""
        app = util.get_newreilc_app('worker', 10.0)
        if app:
            with BackgroundTask(app, name=task_name, group='Task'):
                return self.task_wrapper(task_name, *args, **kwargs)
        else:
            return self.task_wrapper(task_name, *args, **kwargs)

    def task_wrapper(self, task_name, *args, **kwargs):
        try:
            getattr(self, task_name)(*args, **kwargs)
        except OperationInterruptedException as e:
            _logger.warn("Operation interrupted: {}".format(str(e)))
        except Exception as e:
            _logger.exception("%s %s", type(e), str(e))

    def update(self):
        _logger.debug('Starting update')

        torrents_changed = 0

        for item in self.make_pending_list():
            try:
                torrents_changed += self.process_pending_topic(item)
            except (TopicException, TorrentFileException) as e:
                _logger.debug('Failed to proces topic: %s', e)

        _logger.info('%d torrents added/updated', torrents_changed)

        self.invalidate_cache()

    def cleanup(self):
        removed = 0
        # TODO Implement this
        self.invalidate_cache()
        _logger.info('Cleanup finished, %d torrents removed', removed)

    def daily_reset(self):
        """Reset user download counters"""
        with session_scope() as db:
            db.query(User).update({User.downloads_today: 0})
        _logger.info('Daily reset finished')

    def make_pending_list(self):
        """
        Returns list of topics to process
        """
        scraper = Scraper(self.config)
        latest = scraper.get_latest_topics()
        existing = load_topics(latest.keys())

        existing_ids = existing.keys()
        pending = list()

        for tid, topic in latest.items():

            if tid in existing_ids and not topic['changed']:
                continue

            topic['id'] = tid
            topic['new'] = not topic['changed']
            topic['old_infohash'] = existing.get(tid)

            pending.append(topic)

        return pending

    def process_pending_topic(self, item):
        """Process new or updated torrent/topic. Returns 1 if torrent was added
        or updated, 0 otherwise
        :returns int
        """

        tid = item['id']
        user = select_user()
        scraper = Scraper(self.config)
        parsed = scraper.get_topic(tid, user)

        with session_scope() as db:
            db.add(user)

        title = item['title']
        is_new_topic = item['new']
        updated_at = item['updated_at']
        categories = parsed['categories']
        infohash = parsed['infohash']
        old_infohash = item.get('old_infohash')

        category_id = self.ensure_category(categories.pop(), categories)

        # Save topic only if it is new or infohash changed (but not removed)
        if is_new_topic or (infohash and infohash != old_infohash):
            save_topic(tid, category_id, updated_at, title)

        # do not save torrent if no infohash
        if not infohash:
            return 0

        # Torrent new or changed
        if is_new_topic or old_infohash != infohash:
            self.process_torrent(tid, infohash, old_infohash)
            return 1

        return 0


    def ensure_category(self, c_dict, parents):
        """
        Check if category exists, create if not. Create all parent
        categories if needed. Returns category id
        """
        category = find_category(c_dict['tracker_id'], c_dict['is_subforum'])

        if category:
            return category.id

        if parents:
            p_dict = parents.pop()
            parent = find_category(p_dict['tracker_id'], p_dict['is_subforum'])

            if parent:
                parent_id = parent.id
            else:
                parent_id = self.ensure_category(p_dict, parents)
        elif c_dict['tracker_id'] == 0:
            parent_id = None
        else:
            msg = u'No parent category for {}({})'.format(c_dict['tracker_id'],
                                                          c_dict['title'])
            _logger.warn(msg)
            # Skip topic if we can't add its category
            raise TopicException(msg)

        category = Category(
            tracker_id=c_dict['tracker_id'],
            is_subforum=c_dict['is_subforum'],
            title=c_dict['title'],
            parent_id=parent_id,
        )

        with session_scope() as db:
            db.add(category)

        category = find_category(c_dict['tracker_id'], c_dict['is_subforum'])
        _logger.info('Added category %s (%d)', category.title, category.id)

        cache = DiskCache(os.path.join(self.config.DATA_DIR, 'cache'))
        cache_key = 'category_tree.json'
        del cache[cache_key]

        return category.id

    def process_torrent(self, tid, infohash, old_infohash=None):
        scraper = Scraper(self.config)
        user = select_user()
        torrent_dict = None
        retry_count = 0

        while torrent_dict is None and retry_count < 3:
            try:
                # This call can raise TopicException, CaptchaRequiredException
                # or TorrentFileException
                torrent_dict = scraper.get_torrent(tid, user)

            except CaptchaRequiredException:
                # Retry with different user
                user = select_user()
            except DownloadLimitException:  # User reached download limit
                user.downloads_today = user.downloads_limit
                with session_scope() as db:
                    db.add(user)

        user.downloads_today += 1

        with session_scope() as db:
            db.add(user)

        torrentfile = torrent_dict['torrentfile']
        real_infohash = torrent_dict['infohash']
        download_size = torrent_dict['download_size']

        if infohash.lower() != real_infohash.lower():
            msg = 'Torrent {} hash mismatch: {}/{}'.format(tid, infohash,
                                                           real_infohash)
            _logger.error(msg)
            raise TopicException(msg)

        with session_scope() as db:
            torrent = (
                db.query(Torrent)
                .filter(Torrent.infohash == infohash)
                .first()
            )

        if torrent:
            msg = 'Torrent with infohash {} already exists: {}'.format(
                infohash, torrent)
            _logger.error(msg)
            raise TopicException(msg)

        torrent = Torrent(
            id=tid,
            infohash=infohash,
            size=download_size,
            tfsize=len(torrentfile)
        )

        with session_scope() as db:
            db.merge(torrent)

        filename = self.config.TORRENT_PATH_PATTERN.format(tid)

        if old_infohash:
            self.storage.delete(filename)

        self.storage.put(
            filename,
            torrentfile,
            mimetype='application/x-bittorrent'
        )

    def invalidate_cache(self):
        """Invalidates cache for all changed categories. Should be called after
        all operations that may add, change or delete topics/torrents"""
        for category_id in self.changed_categories:
            pass  # TODO implement this

    def sync_categories(self):
        """Import all existing tracker categories into DB"""
        _logger.info('Syncing tracker categories')
        user = select_user(False)
        scraper = Scraper(self.config)

        with session_scope() as db:
            old = db.query(func.count(Category.id)).scalar()

            root = db.query(Category).get(0)
            if not root:  # Create root category
                root = Category(
                    id=0,
                    title=u'Все разделы',
                    parent_id=None,
                    tracker_id=0,
                    is_subforum=False,
                )
                db.add(root)

        for forum_id in scraper.get_forum_ids(user):
            category = find_category(forum_id, True)

            if category:
                continue

            try:
                cat_list = scraper.get_forum_categories(forum_id, user)
            except ItemProcessingFailedException as e:
                _logger.error("Failed to import category: {}".format(e))

            if not cat_list:
                _logger.warn('Unable to get category list for %d', forum_id)
                continue

            self.ensure_category(cat_list.pop(), cat_list)

        new = db.query(func.count(Category.id)).scalar()

        _logger.info("Category sync completed, %d old, %d added", old,
                     new - old)

    def populate_categories(self, count=1, total=None):
        """
        Add count (or less) torrents to every category with less then count
        torrents, no more than total torrents
        """
        with session_scope() as db:
            query = (
                db.query(Category, func.count(Torrent.id))
                .outerjoin(Topic)
                .outerjoin(Torrent)
                .filter(Category.is_subforum)
                .group_by(Category.id)
                .having(func.count(Torrent.id) < count)
                .order_by(Category.id)
            )

            categories = query.all()
            db.expunge_all()

        if total is None:
            if count == 1:
                total = len(categories)
            else:
                raise ValueError('total parameter is required if count > 1')

        message = (
            'Found {} categories with <{} torrents, '
            'going to download up to {} torrents'
            .format(len(categories), count, total)
        )
        _logger.info(message)

        if not len(categories):
            return


        total_added = 0

        for cat, num_torrents in categories:
            # If this category has some torrents - only add missing amount
            to_add = count - num_torrents

            # Do not add more than total
            if total_added + to_add > total:
                to_add = total - total_added

            added = self.populate_category(cat.tracker_id, to_add)
            total_added += added
            _logger.debug('Added %d torrents to %s ', added, cat.title)

            if total_added >= total:
                break

        _logger.info('Populate task added %d torrents', total_added)

    def populate_category(self, forum_id, count):
        """
        Add count torrents from subforum forum_id
        :returns int Number of torrents added
        """
        scraper = Scraper(self.config)
        user = select_user()
        try:
            torrents = scraper.find_torrents(user, forum_id)
        except ItemProcessingFailedException as e:
            msg = "Failed to populate category {}: {}".format(forum_id, e)
            _logger.error(msg)
            torrents = []

        with session_scope() as db:
            db.add(user)

        if not torrents:
            _logger.debug('No torrents found in category %d', forum_id)
            return 0

        added = 0

        for tdict in torrents:
            with session_scope() as db:
                exists = db.query(Topic).get(tdict['id'])

            # Skip torrents that are already in database
            if exists:
                continue

            tdict['new'] = True
            try:
                added += self.process_pending_topic(tdict)

            except TopicException:
                _logger.debug('Failed to add topic %d', tdict['id'])

            if added == count:
                break

        return added

    def daily_populate_task(self):
        dlslots = estimate_free_download_slots()
        # _logger.info("Daily populate going to download %d torrents", dlslots)
        self.populate_categories(KEEP_TORRENTS_MIN, dlslots)


def select_user(with_dlslots=True):
    """
    Select one random user, if can_download is true then user must have
    download slots available
    :returns User
    """
    with session_scope() as db:
        try:
            query = db.query(User).filter(User.enabled.is_(True))

            if with_dlslots:
                query = query.filter(or_(
                    User.downloads_limit > User.downloads_today,
                    User.downloads_limit.is_(None)
                ))

            user = query.order_by(func.random()).limit(1).one()

        except NoResultFound:
            raise OperationInterruptedException('No suitable users found')
        else:
            db.expunge(user)

    return user


def load_topics(ids):
    """
    Loads existing topics from database
    :returns dict(topic_id: infohash)
    """
    topics = dict()
    with session_scope() as db:
        existing = (
            db.query(Topic)
            .options(joinedload(Topic.torrent))
            .filter(Topic.id.in_(ids))
            .all()
        )
        for t in existing:
            topics[t.id] = t.torrent.infohash if t.torrent else None

    return topics


def save_topic(tid, category_id, updated_at, title):
    """
    Insert or update topic.
    """
    topic = Topic(
        id=tid,
        category_id=category_id,
        title=title,
        updated_at=updated_at
    )

    _logger.debug('Saving topic %s', topic)
    with session_scope() as db:
        topic = db.merge(topic)
        db.commit()


def find_category(tracker_id, is_subforum):
    with session_scope() as db:
        category = (
            db.query(Category).filter(
                Category.tracker_id == tracker_id,
                Category.is_subforum == is_subforum
            ).first()
        )
        db.expunge_all()
    return category


def estimate_free_download_slots(days=7):
    """Calculates estimated download slots available based on number
    of torrents, downloaded each day during past week
    """
    today = datetime.datetime.utcnow().date()
    week = (datetime.datetime.utcnow() - datetime.timedelta(days)).date()
    with session_scope() as db:
        num_downloads = (
            db.query(func.count(Torrent.id))
            .join(Topic)
            .filter(func.date(Topic.updated_at) >= week)
            .filter(func.date(Topic.updated_at) < today)
            .scalar()
        )

        daily_slots = (
            db.query(func.sum(User.downloads_limit))
            .filter(User.enabled)
            .scalar()
        )

        slots_left_today = (
            db.query(func.sum(User.downloads_limit - User.downloads_today))
            .filter(User.enabled)
            .scalar()
        )

    estimate = daily_slots - (num_downloads / days)

    if estimate > slots_left_today:
        estimate = slots_left_today

    if estimate > 1000:
        estimate = 1000

    return int(estimate * 0.9)
