import hashlib

import bencode


class TorrentFile(object):
    def __init__(self, initdata):
        if isinstance(initdata, dict):
            self._decoded = initdata.copy()
            self._encoded = None
        elif isinstance(initdata, str):
            self._encoded = initdata
            self._decoded = None
        else:
            raise ValueError('Torrent initial data must be string or dict')

    def get_encoded(self):
        if self._encoded is None:
            self._encoded = bencode.bencode(self._decoded)
        return self._encoded

    def set_encoded(self, encoded):
        self._encoded = encoded
        self._decoded = None

    encoded = property(get_encoded, set_encoded)

    def get_decoded(self):
        if self._decoded is None:
            try:
                self._decoded = bencode.bdecode(self._encoded)
            except bencode.BTFailure as e:
                raise ValueError('Failed to decode torrent file: {}'.format(e))
        return self._decoded

    def set_decoded(self, decoded):
        self._decoded = decoded
        self._encoded = None

    decoded = property(get_decoded, set_decoded)

    @property
    def infohash(self):
        """Calculates torrent infohash"""
        info = bencode.bencode(self.decoded['info'])
        return hashlib.sha1(info).hexdigest()

    @property
    def download_size(self):
        """Calculates torrent size"""
        length = self.decoded['info'].get('length', 0)
        if length:
            return length

        for entry in self.decoded['info']['files']:
            length += entry['length']

        return length

    def remove_announcers_with_passkeys(self):
        """Remove all announce urls with user passkey"""
        if '?uk=' in self.decoded['announce']:
            self.decoded.pop('announce', None)
        ann_list = self.decoded['announce-list']
        newlist = filter(lambda a: '?uk=' not in a[0], ann_list)
        self.decoded['announce-list'] = newlist
        self._encoded = None

    def add_announcer(self, announcer):
        self.decoded['announce'] = announcer
        if 'announce-list' not in self.decoded:
            self.decoded['announce-list'] = list()
        self.decoded['announce-list'].append([announcer])
        self._encoded = None
