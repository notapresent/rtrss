'''All exceptions are defined in this module'''

class OperationInterruptedException(Exception):
    '''Raised if unrecoverable error occured during any operation'''
    pass


class CaptchaRequiredException(Exception):
    '''Raised if user exceeds torrent download quota'''
    pass


class TopicException(Exception):
    '''Raised if error occured during topic processing'''
    pass
