import logging

# logging.disable(logging.ERROR)
logging.basicConfig(level=logging.DEBUG)

DB_URL = 'postgresql://postgres:postgres@localhost/rtrss_test'


class MockConfig(dict):
    def __getattr__(self, name):
        if name in self:
            return self.get(name)
        else:
            raise ValueError('Config key {} not found'.format(name))
