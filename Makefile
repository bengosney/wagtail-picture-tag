.PHONY := install, help, init, pre-init, css, pip
.DEFAULT_GOAL := install

HOOKS=$(.git/hooks/pre-commit)
INS=$(wildcard requirements.*.in)
REQS=$(subst in,txt,$(INS))

SCSS_PARTIALS=$(wildcard scss/_*.scss)
SCSS=$(filter-out scss/_%.scss,$(wildcard scss/*.scss))
CSS=$(subst scss,css,$(SCSS))

HEROKU_APP_NAME=rhgs
DB_USER=rhgs
DB_PASS=rhgs
DB_NAME=rhgs
DB_CONTAINER_NAME=rhgs-postgres

help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.envrc: 
	@echo layout python python3.10 > $@
	@echo "Created .envrc, run make again"
	@touch requirements.in
	@touch $(INS)
	direnv exec . make init
	@false

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
