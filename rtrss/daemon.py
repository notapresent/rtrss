import os
import logging

from rtrss.basedaemon import BaseDaemon


_logger = logging.getLogger(__name__)


class WorkerDaemon(BaseDaemon):
    def run(self):
        _logger.info('Daemon started with pid %d', os.getpid())

        from rtrss.worker import worker_action, setup_external_logging

        setup_external_logging()
        worker_action('run')

        _logger.info('Daemon is done and exiting')

    def start(self):
        _logger.info('Starting daemon')
        super(WorkerDaemon, self).start()

    def stop(self):
        _logger.info('Stopping daemon')
        super(WorkerDaemon, self).stop()

    def restart(self):
        _logger.info('Restarting daemon')
        super(WorkerDaemon, self).restart()


def make_daemon(config):
    """Returns WorkerDaemon instance"""
    pidfile = os.path.join(config.DATA_DIR, 'daemon.pid')
    logdir = os.environ.get('OPENSHIFT_LOG_DIR') or config.DATA_DIR
    logfile = os.path.join(logdir, 'debug.log')
    return WorkerDaemon(pidfile, stdout=logfile, stderr=logfile)
