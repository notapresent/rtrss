.PHONY: all test

all: test

test:
	python -m unittest discover

clean: clean-pyc clean-data

clean-pyc:
	find . -name '*.pyc' -exec rm {} \;
	find . -name '__pycache__' -type d | xargs rm -rf

clean-data:
	rm -rf ./data/*.log
	rm ./data/*.html
