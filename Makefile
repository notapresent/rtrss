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
	sed -e "s;###LOG_DIR###;${OPENSHIFT_LOG_DIR};g" -e "s;###TMP_DIR###;${OPENSHIFT_TMP_DIR};g" -e "s;###DATA_DIR###;${OPENSHIFT_DATA_DIR};g" supervisord-openshift.template.ini > supervisord-openshift.conf
