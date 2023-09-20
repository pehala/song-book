.PHONY: commit-acceptance pylint black reformat pre-commit locale migrations deploy check-fuzzy run

commit-acceptance: black pylint
pre-commit: messages migrations reformat

RUN = poetry run
MANAGE = $(RUN) python manage.py

SETTINGS ?= chords.settings.production

pylint:
	$(RUN) pylint backend/ chords/ pdf/ frontend/ category/ analytics/ tenants/ --django-settings-module=$(SETTINGS)

black:
	$(RUN) black --check . --diff

reformat:
	$(RUN) black .

check-fuzzy:
	@ for app in "backend" "chords" "pdf" "frontend" "category" "analytics" "tenants" ; do \
  		if [ ! -z "$$(msgattrib $${app}/locale/cs/LC_MESSAGES/django.po --only-fuzzy)" ]; then echo "$${app} app contains fuzzy strings" && exit 1; fi \
	done;

messages:
	$(MANAGE) makemessages -l cs

migrations:
	$(MANAGE) makemigrations

deploy: ## Deploys to production
	$(MANAGE) migrate
	$(MANAGE) compilescss
	$(MANAGE) prerender
	$(MANAGE) compilemessages
	$(MANAGE) collectstatic --noinput

init: ## Initializes project for development
	cp chords/settings/production.py.tpl chords/settings/production.py
	$(MANAGE) migrate

run: ## Runs the development server
	$(MANAGE) runserver --settings $(SETTINGS)

# Check http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## Print this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# this ensures dependent target is run everytime
FORCE: