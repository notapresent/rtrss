import sys
import resource

from sqlalchemy import func

from rtrss.models import *

def get_stats(db):
    tc = db.query(func.count(Topic.id))
    tts = db.query(func.sum(Torrent.tfsize))

    cats_total = db.query(func.count(Category.id))
    cats_wt = db.query(func.count(Topic.category_id.distinct())).join(Torrent)

    total_dlslots = db.query(func.sum(User.downloads_limit))
    used_dlslots = db.query(func.sum(User.downloads_today))

    row = db.query(
        func.count(Torrent.id).label('tfc'),
        tc.as_scalar().label('tc'),
        tts.as_scalar().label('tts'),

        cats_total.as_scalar().label('cats_total'),
        cats_wt.as_scalar().label('cats_wt'),

        total_dlslots.as_scalar().label('total_dlslots'),
        used_dlslots.as_scalar().label('used_dlslots'),
    ).one()

    result = {
        'total_torrents': row.tfc,
        'total_topics': row.tc,
        'total_torrentfile_size': row.tts,

        'categories_total': row.cats_total,
        'categories_with_torrents': row.cats_wt,

        'total_dlslots': row.total_dlslots,
        'used_dlslots': row.used_dlslots,

        'memory_usage': memory_usage_resource()
    }

    return result

def memory_usage_resource():
    rusage_denom = 1024.
    if sys.platform == 'darwin':
        # ... it seems that in OSX the output is different units ...
        rusage_denom = rusage_denom * rusage_denom
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / rusage_denom
    return mem
