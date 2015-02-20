"""All exceptions are defined in this module"""


class OperationInterruptedException(Exception):
    """Raised if unrecoverable error occurred during any operation"""
    pass


class CaptchaRequiredException(Exception):
    """Raised if user exceeds torrent download quota"""
    pass


class DownloadLimitException(Exception):
    """Raised if user exceeds torrent download quota"""
    pass


class ItemProcessingFailedException(Exception):
    """
    Raised if processing topic/forum/category failed but execution may continue
    """
    pass


class TorrentFileException(Exception):
    """Raised if user unable to download torrent"""
    pass


class TopicException(ItemProcessingFailedException):
    """Raised if error occurred during topic processing"""
    pass
