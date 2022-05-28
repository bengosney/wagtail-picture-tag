.PHONY := install, help, init, pre-init, css, pip
.DEFAULT_GOAL := install

HOOKS=$(.git/hooks/pre-commit)
INS=$(wildcard requirements.*.in)
REQS=$(subst in,txt,$(INS))

PYTHONFILES=$(wildcard ./**/*.py)

dist: $(PYTHONFILES) setup.py pyproject.toml
	python -m build
	@touch dist

pypi: dist ## Deploy to the actual PyPI
	python -m twine upload dist/*

pypi-test: dist ## Deploy to the test PyPI
	python3 -m twine upload --verbose --repository testpypi dist/*

help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

requirements.%.txt: requirements.%.in requirements.txt
	@echo "Builing $@"
	@pip-compile --generate-hashes -q -o $@ $<
	@touch $@

requirements.txt: requirements.in
	@echo "Builing $@"
	@pip-compile --generate-hashes -q $^

pip: requirements.txt $(REQS) ## Install development requirements
	@echo "Installing $^"
	@pip-sync $^

install: pip

$(HOOKS):
	pre-commit install

pre-init:
	pip install --upgrade pip
	pip install wheel pip-tools

init: .envrc pre-init install $(HOOKS) ## Initalise a dev enviroment
	@which direnv > /dev/null || echo "direnv not found but recommended"
	@echo "Read to dev"

clean:
	@echo "Cleaning up"
	@rm -rf *.egg-info images original_images
