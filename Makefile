.PHONY: commit-acceptance pylint black reformat pre-commit locale migrations deploy

commit-acceptance: black pylint
pre-commit: locale migrations

RUN = poetry run
MANAGE = $(RUN) python manage.py

SETTINGS ?= chords.settings.production

pylint:
	$(RUN) pylint backend/ chords/ pdf/ frontend/ category/ analytics/ --django-settings-module=$(SETTINGS)

black:
	$(RUN) black --check . --diff

reformat:
	$(RUN) black .

locale:
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