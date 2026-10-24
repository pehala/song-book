.PHONY: commit-acceptance pylint black reformat pre-commit locale migrations deploy check-fuzzy check-messages messages messages-js run test coverage e2e \
	image migrate prerender cache_clear compilemessages collectstatic compress_static export_static start worker

commit-acceptance: ruff reformat check-fuzzy check-messages
pre-commit: messages migrations reformat

# The container image sets RUN empty: its virtualenv is already on PATH and it has no uv
RUN ?= uv run
MANAGE ?= $(RUN) python manage.py

SETTINGS ?= chords.settings.production

ruff:
	$(RUN) ruff check . --fix

reformat:
	$(RUN) ruff format .

check-fuzzy:
	@ for po in django djangojs; do \
		file=chords/locale/cs/LC_MESSAGES/$$po.po; \
		if [ ! -z "$$(msgattrib $$file --only-fuzzy)" ]; then echo "$$file contains fuzzy strings" && exit 1; fi; \
	done

# Fails when a catalogue is not what `make messages` produces, or the reader's one has an untranslated string
check-messages: messages
	@ git diff --exit-code -I'^"POT-Creation-Date' -- chords/locale/cs/LC_MESSAGES/django.po chords/locale/cs/LC_MESSAGES/djangojs.po || { echo "run make messages and commit the result"; exit 1; }
	@ if [ ! -z "$$(msgattrib chords/locale/cs/LC_MESSAGES/djangojs.po --untranslated)" ]; then echo "djangojs.po contains untranslated strings" && exit 1; fi

messages: messages-js
	$(MANAGE) makemessages -l cs

messages-js:
	$(MANAGE) makemessages -l cs -d djangojs -i "*/vendor/*" -i "backend/static/*" -i "pdf/static/*" -i "*/templates/*" -i "staticfiles/*"

migrations:
	$(MANAGE) makemigrations

deploy: migrate prerender compilemessages collectstatic ## Deploys to production

migrate: ## Applies database migrations
	$(MANAGE) migrate --noinput

prerender: ## Prerenders markdown of every song
	$(MANAGE) prerender

cache_clear: ## Clears the Django cache (Huey's queue lives in another Redis db and stays)
	$(MANAGE) shell -c "from django.core.cache import cache; cache.clear()"

compilemessages: ## Compiles translations
	$(MANAGE) compilemessages

collectstatic: ## Collects and fingerprints static files into chords/static
	$(MANAGE) collectstatic --noinput

# Lets nginx serve them with brotli_static/gzip_static instead of compressing on every request.
# Fonts, images and woff2 are already compressed.
compress_static: ## Writes maximally compressed .br and .gz siblings of collected static files
	find chords/static -type f -size +1k -regextype posix-extended \
		-regex '.*\.(css|js|mjs|json|svg|txt|map|ttf|otf|eot|ico|html|xml)$$' \
		-exec brotli -k -f -Z {} + \
		-exec gzip -k -f -9 {} +

# Older fingerprinted files in the target are kept, so pages still open in browsers keep working
export_static: ## Copies collected static files to STATIC_EXPORT_DIR for nginx
	$(if $(STATIC_EXPORT_DIR),,$(error STATIC_EXPORT_DIR is not set))
	set -o pipefail; cd chords/static && tar -cf - -- * | tar -C $(STATIC_EXPORT_DIR) -xf - --no-same-owner

start: ## Runs gunicorn as configured for the container image
	$(RUN) gunicorn --config deploy/gunicorn.conf.py

IMAGE ?= localhost/songbook:latest

image: ## Builds the container image (see deploy/DEPLOY.md)
	podman build -t $(IMAGE) \
		--build-arg BUILD_DATE=$$(git log -1 --format=%ad --date=format:%Y/%m/%d) \
		--build-arg BUILD_REVISION=$$(git rev-parse --short HEAD) .

init: ## Initializes project for development
	cp chords/settings/production.py.tpl chords/settings/production.py
	$(MANAGE) migrate

test: ## Runs the test suite
	uv run --group dev pytest tests/

e2e: ## Runs the browser tests of the reader (needs: uv run playwright install --with-deps chromium)
	uv run --group dev pytest tests/e2e -m e2e --tracing retain-on-failure

coverage: ## Runs the test suite and reports coverage
	uv run --group dev pytest tests/ --cov

run: ## Runs the development server
	$(MANAGE) runserver --settings $(SETTINGS)

worker: ## Runs the Huey PDF worker
	$(MANAGE) run_huey --settings $(SETTINGS) --worker-type process

# Check http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## Print this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# this ensures dependent target is run everytime
FORCE: