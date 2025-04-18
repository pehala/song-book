.PHONY: commit-acceptance pylint black reformat pre-commit locale migrations deploy check-fuzzy run

commit-acceptance: black pylint check-fuzzy
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
	@ if [ ! -z "$$(msgattrib chords/locale/cs/LC_MESSAGES/django.po --only-fuzzy)" ]; then echo "chords/locale/cs/LC_MESSAGES/django.po contains fuzzy strings" && exit 1; fi

messages:
	$(MANAGE) makemessages -l cs

migrations:
	$(MANAGE) makemigrations

deploy: ## Deploys to production
	$(MANAGE) migrate
	$(MANAGE) prerender
	$(MANAGE) compilemessages
	$(MANAGE) collectstatic --noinput

init: ## Initializes project for development
	cp chords/settings/production.py.tpl chords/settings/production.py
	$(MANAGE) migrate

run: ## Runs the development server
	$(MANAGE) runserver --settings $(SETTINGS)

worker: ## Runs the Huey PDF worker
	$(MANAGE) run_huey --settings $(SETTINGS) --worker-type process

# Check http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## Print this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# this ensures dependent target is run everytime
FORCE: