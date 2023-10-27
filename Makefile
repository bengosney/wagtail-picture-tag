.PHONY: help clean test install all init dev pypi
.DEFAULT_GOAL := install
.PRECIOUS: requirements.%.in

HOOKS=$(.git/hooks/pre-commit)
INS=$(wildcard requirements.*.in)
REQS=$(subst in,txt,$(INS))

PYTHONFILES=$(wildcard ./wagtail_picture_tag/**/*.py)

PYTHON_VERSION:=$(shell python --version | cut -d " " -f 2)
PIP_PATH:=.direnv/python-$(PYTHON_VERSION)/bin/pip
WHEEL_PATH:=.direnv/python-$(PYTHON_VERSION)/bin/wheel
PIP_SYNC_PATH:=.direnv/python-$(PYTHON_VERSION)/bin/pip-sync
PRE_COMMIT_PATH:=.direnv/python-$(PYTHON_VERSION)/bin/pre-commit


$(PIP_PATH): .direnv
	@python -m ensurepip
	@python -m pip install --upgrade pip

$(WHEEL_PATH): $(PIP_PATH) .direnv
	@python -m pip install wheel

$(PIP_SYNC_PATH): $(PIP_PATH) $(WHEEL_PATH) .direnv
	@python -m pip install pip-tools

$(PRE_COMMIT_PATH): $(PIP_PATH) $(WHEEL_PATH) .direnv
	@python -m pip install pre-commit

dist: $(PYTHONFILES) pyproject.toml
	python -m build
	@touch dist

check: dist ## Run twine check
	python -m twine check $^/*

pypi: dist check ## Deploy new version to PyPI
	python -m twine upload dist/*

pypi-test: dist check ## Test Deploy to new version to Test PyPI
	python3 -m twine upload --verbose --repository testpypi dist/*

help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.gitignore:
	curl -q "https://www.toptal.com/developers/gitignore/api/visualstudiocode,python,direnv" > $@

.git: .gitignore
	git init

.git/hooks/pre-commit: .git $(PRE_COMMIT_PATH)
	pre-commit install

.pre-commit-config.yaml: .git/hooks/pre-commit $(PRE_COMMIT_PATH)
	curl https://gist.githubusercontent.com/bengosney/4b1f1ab7012380f7e9b9d1d668626143/raw/060fd68f4c7dec75e8481e5f5a4232296282779d/.pre-commit-config.yaml > $@
	pre-commit autoupdate

requirements.%.in:
	echo "-c requirements.txt" > $@

requirements.%.txt: requirements.%.in requirements.txt
	@echo "Builing $@"
	@python -m piptools compile -q -o $@ $^

requirements.txt: pyproject.toml
	@echo "Builing $@"
	@python -m piptools compile -q $^

.direnv: .envrc
	python -m pip install --upgrade pip
	python -m pip install wheel pip-tools
	@touch $@ $^

.envrc:
	@echo "Setting up .envrc then stopping"
	@touch -d '+10 minute' $@
	@echo "layout python python3.10" > $@
	@false

init: .direnv .git .git/hooks/pre-commit requirements.dev.txt ## Initalise a enviroment

clean: ## Remove all build files
	@find . -maxdepth 3 -name '*.pyc' -delete || true
	@find . -maxdepth 3 -type d -name '__pycache__' -exec rm -rf {} \; || true
	@rm -rf .pytest_cache
	@rm -f .testmondata
	@rm -f .coverage*

install: $(PIP_SYNC_PATH) requirements

requirements: requirements.txt $(REQS) ## Install development requirements (default)
	@echo "Installing $^"
	@python -m piptools sync $^

upgrade: requirements.txt $(REQS)
	python -m piptools compile -U pyproject.toml
	python -m piptools compile -U $(INS)
	$(MAKE) install
	python -m pre_commit autoupdate
	python -m pre_commit run --all

dev: init install ## Start work
	code .

LICENCE:
	@curl -q https://www.gnu.org/licenses/gpl-3.0.txt > $@

coverage.lcov: $(PYTHONFILES)
	python -m pytest --cov=. --cov-report lcov
