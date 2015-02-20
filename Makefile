.PHONY: all test

all: test

test:
	RTRSS_ENVIRONMENT='testing' python -m unittest discover

retest:
	RTRSS_ENVIRONMENT='testing' rerun --verbose --ignore=./tmp* --ignore=data --ignore=.idea "python -m unittest discover"

clean: clean-pyc clean-data

clean-pyc:
	find . -name '*.pyc' -exec rm {} \;
	find . -name '__pycache__' -type d | xargs rm -rf

clean-data:
	rm -rf ./data/*.log
	rm ./data/*.html

create-supervisord-conf:
	echo "Generating supervisord config file"
	sed -e "s;###LOG_DIR###;${OPENSHIFT_LOG_DIR};g" -e "s;###TMP_DIR###;${OPENSHIFT_TMP_DIR};g" -e "s;###DATA_DIR###;${OPENSHIFT_DATA_DIR};g" conf/supervisord-openshift.template.ini > "${OPENSHIFT_REPO_DIR}supervisord.conf"

create-leagent-conf:
	echo "Generating logentries agent config file"
	sed -e "s;###USER_KEY###;${LOGENTRIES_USER_KEY};g" -e "s;###AGENT_KEY###;${LOGENTRIES_AGENT_KEY};g" conf/le_config.template.ini > "${OPENSHIFT_DATA_DIR}.le/config"
