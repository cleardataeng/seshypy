.PHONY: clean clean-build clean-pyc clean-test coverage deploy-docs dist docs docs help install lint release test
.DEFAULT_GOAL := help

help:
	$(info available targets:)
	@awk '/^[a-zA-Z\-\_0-9\.\$$\(\)\%/]+:/ { \
		helpMsg = $$0; \
		nb = sub(/^[^:]*:.* ## /, "", helpMsg); \
		if (nb) \
			print  $$1 "\t" helpMsg; \
	}' \
	$(MAKEFILE_LIST) | column -ts $$'\t' | \
	grep --color '^[^ ]*'

# project variables
PROJECT_NAME := seshypy
PROJECT_NAME_NODASH := seshypy
VERSION := $(shell git describe --always --dirty)

define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

clean: clean-test clean-build clean-pyc ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

coverage: ## check code coverage quickly with the default Python
	coverage run --source seshypy setup.py test
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/seshypy.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ seshypy
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

install: clean ## install the package to the active Python's site-packages
	python setup.py install

lint: ## check style with flake8
	flake8 seshypy tests

publish: req-publish-registry
	python setup.py sdist upload -r $(PUBLISH_REGISTRY)
	python setup.py bdist_wheel upload -r $(PUBLISH_REGISTRY)

release: req-release-type req-release-repo clean ## package and upload a release
	release -t $(RELEASE_TYPE) -g $(RELEASE_REPO) $(RELEASE_BRANCH) $(RELEASE_BASE)

req-publish-registry:
ifndef PUBLISH_REGISTRY
	$(error PUBLISH_REGISTRY is undefined)
endif

req-release-type:
ifndef RELEASE_TYPE
	$(error RELEASE_TYPE is undefined)
endif

req-release-repo:
ifndef RELEASE_REPO
	$(error RELEASE_REPO is undefined)
endif

test: ## run tests quickly with the default Python
	python setup.py test

tox:
	tox -p 2 -o
