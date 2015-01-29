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

# Run new relic agent if we have license key
if 'NEW_RELIC_LICENSE_KEY' in os.environ:
    import newrelic.agent
    newrelic.agent.initialize()

from rtrss.webapp2 import app as application

#
# Below for testing only
#
if __name__ == '__main__':
    from rtrss import config
    application.run(config.IP, config.PORT, debug=True)
