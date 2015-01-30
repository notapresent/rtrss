import os
import logging

from rtrss.basedaemon import BaseDaemon
from rtrss import util, config, scheduler


_logger = logging.getLogger(__name__)


class WorkerDaemon(BaseDaemon):
    def run(self):
        _logger.info('Daemon started with pid %d', os.getpid())

        util.init_newrelic_agent()
        util.setup_logging('daemon')
        util.setup_logentries_logging('LOGENTRIES_TOKEN_WORKER')

        sched = scheduler.Scheduler(config)
        return sched.run()

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


def make_daemon(cfg):
    """Returns WorkerDaemon instance"""
    pidfile = os.path.join(cfg.DATA_DIR, 'daemon.pid')
    logdir = os.environ.get('OPENSHIFT_LOG_DIR') or cfg.DATA_DIR
    logfile = os.path.join(logdir, 'daemon-stderr.log')
    return WorkerDaemon(pidfile, stdout=None, stderr=logfile)


def get_status_string(instance):
    """Return daemon status string"""
    running = instance.is_running()
    if running:
        with open(instance.pidfile, 'r') as f:
            pid = f.read().strip()
        msg = "Daemon is running with pid {}".format(pid)
    else:
        msg = "Daemon is not running"
    return msg
