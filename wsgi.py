#!/usr/bin/python
import os

if os.environ.get('OPENSHIFT_PYTHON_DIR'):      # on Openshift
    virtenv = os.environ.get('OPENSHIFT_PYTHON_DIR') + '/virtenv/'
    virtualenv = os.path.join(virtenv, 'bin/activate_this.py')
    execfile(virtualenv, dict(__file__=virtualenv))

#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
#

from rtrss import util

util.setup_logging('webapp')
util.setup_logentries_logging('LOGENTRIES_TOKEN_WEBAPP')
util.init_newrelic_agent()

from rtrss.webapp import app as application

#
# Below for testing only
#
if __name__ == '__main__':
    from rtrss import config
    application.run(config.IP, config.PORT, debug=True)
