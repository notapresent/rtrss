"""All exceptions are defined in this module"""


class OperationInterruptedException(Exception):
    """Raised if unrecoverable error occured during any operation"""
    pass


class CaptchaRequiredException(Exception):
    """Raised if user exceeds torrent download quota"""
    pass


class TorrentFileException(Exception):
    """Raised if user unable to download torrent"""
    pass


class TopicException(Exception):
    """Raised if error occurred during topic processing"""
    pass
