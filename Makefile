.PHONY := install, help, init, pre-init, css, pip
.DEFAULT_GOAL := install

HOOKS=$(.git/hooks/pre-commit)
INS=$(wildcard requirements.*.in)
REQS=$(subst in,txt,$(INS))

PYTHONFILES=$(wildcard ./**/*.py)

dist: $(PYTHONFILES) setup.cfg pyproject.toml README.rst
	python -m build
	@touch dist

check: dist
	python -m twine check $^/*

pypi: dist check ## Deploy to the actual PyPI
	python -m twine upload dist/*

pypi-test: dist check ## Deploy to the test PyPI
	python -m twine upload --verbose --repository testpypi dist/*

help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

requirements.%.txt: requirements.%.in requirements.txt
	@echo "Builing $@"
	@python -m piptools compile -q -o $@ $<
	@touch $@

requirements.txt: requirements.in
	@echo "Builing $@"
	@python -m piptools compile -q $^

pip: requirements.txt $(REQS) ## Install development requirements
	@echo "Installing $^"
	@python -m piptools sync $^

install: pip

$(HOOKS):
	python -m pre-commit install

pre-init:
	python -m pip install --upgrade pip
	python -m pip install wheel pip-tools

init: .envrc pre-init install $(HOOKS) ## Initalise a dev enviroment
	@which direnv > /dev/null || echo "direnv not found but recommended"
	@echo "Read to dev"

clean:
	@echo "Cleaning up"
	@rm -rf *.egg-info images original_images
	@rm -rf dist build
