.PHONY: all test

all: test

test:
	RTRSS_ENVIRONMENT='testing' python -m unittest discover

retest:
	RTRSS_ENVIRONMENT='testing' rerun --verbose --ignore=data --ignore=.idea "python -m unittest discover"

clean: clean-pyc clean-data

clean-pyc:
	find . -name '*.pyc' -exec rm {} \;
	find . -name '__pycache__' -type d | xargs rm -rf

clean-data:
	rm -rf ./data/*.log
	rm ./data/*.html
