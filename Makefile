.PHONY: commit-acceptance pylint black reformat pre-commit locale migrations deploy

commit-acceptance: black pylint
pre-commit: locale migrations

pylint:
	poetry run pylint backend/ chords/ pdf/ frontend/ category/ analytics/ --django-settings-module=chords.settings.development

black:
	poetry run black --check . --diff

reformat:
	poetry run black .

locale:
	poetry run python manage.py makemessages -l cs

migrations:
	poetry run python manage.py makemigrations

deploy:
	poetry run python manage.py migrate
	poetry run python manage.py compilescss
	poetry run python manage.py prerender
	poetry run python manage.py compilemessages
	poetry run python manage.py collectstatic --noinput

# Check http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## Print this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# this ensures dependent target is run everytime
FORCE: