import logging

logging.disable(logging.ERROR)
# logging.basicConfig(level=logging.DEBUG)

# TODO Move this somewhere
DB_URL = 'postgresql://postgres:postgres@localhost/rtrss_test'


class AttrDict(dict):
    '''Class to make mock config objects'''
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
