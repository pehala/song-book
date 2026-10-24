 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
 
# Song book
This project aims to create a song book for storing, managing and viewing songs. The songs are loaded once and then all the filtering/searching happens on the client, which enables it to be used even in low-internet environment. It can also automatically generate PDFs of the selected categories. Songs use Markdown with custom extensions for chords

## Features

* Use markdown to add songs
* Load-once site with all songs available
* Categorize songs into different Categories
* Generate PDFs of the selected categories/songs automatically
* Host multiple site (based on hostname) with only one instance

# Running in production

The recommended way is the container image with Podman quadlets, described in [deploy/DEPLOY.md](deploy/DEPLOY.md). To run it without containers:

* Override any setting you want in `chords/settings/production.py`
  * Set `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` to actual domain you want the site to exist on
  * Generate `SECRET_KEY` unique for this site (https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SECRET_KEY)
  * Override both `CACHES` and `DATABASES` to point to your Redis and PostgreSQL (or other DB engine) respectively
  * Set `TENANT_HOSTNAME` to the hostname that the site should use
  * Keep `DEBUG = False`: besides the debug pages, `DEBUG` makes Django emit unhashed static URLs, and the
    10-year cache on `/static/` would then serve stale files after every deploy
  * Keep `USE_PRERENDERED_MARKDOWN = True` (and `USE_DYNAMIC_PRERENDER = True` as a safety net) so songs are
    rendered once on save instead of on every request; `make deploy` runs `prerender` for existing rows
* Setup gunicorn or any other WSGI server
* Setup Worker
  * `uv run python manage.py run_huey --worker-type process`
  * Responsible for async PDF generation
* Setup NGINX or any other reverse proxy to expose the website (see below)

## nginx

Compression happens in nginx only; the app never sets `Content-Encoding`. Static files are pre-compressed at deploy
time (`brotli --quality=11`) and served as-is; dynamic responses (HTML, the songs JSON) are compressed on the fly.
Brotli level 9 is the sweet spot for the ~850 KB songs JSON: levels 10–11 save another 10 KB but cost 10–25× the
CPU per uncached response. With `DEBUG = False` Django no longer serves `/media/`, so nginx must.

```nginx
# dynamic responses from gunicorn
brotli on; brotli_comp_level 9;
brotli_types text/html text/css application/javascript application/json image/svg+xml application/manifest+json;
gzip on; gzip_vary on; gzip_comp_level 6;
gzip_types text/html text/css application/javascript application/json image/svg+xml application/manifest+json;

# content-hashed static files, pre-compressed by the deploy script
location /static/ {
    brotli_static on; expires max;
    add_header Cache-Control "public, max-age=31536000, immutable";
    add_header Vary Accept-Encoding;
}

# tenant icons and generated PDFs
location /media/ { expires 30d; add_header Cache-Control "public"; }
```

`add_header` inside a `location` replaces inherited headers, so repeat any global ones there.

# Developing

## Dependencies

* Python 3.12+
* [gettext](https://www.gnu.org/software/gettext/)
    * Used for compiling locales
* [Redis](https://redis.io/)
    * Used as both cache and messaging queue for PDF generation

## Getting Started

First clone the repository from GitHub and switch to the new directory:

    git clone https://github.com/pehala/song-book.git
    cd song-book
    
Install uv and dependencies

    pip install uv
    uv sync --group dev
    
Then simply initialize the website:

    make init

You can now run the development server:

    make run


## PDF generation

Song book can generate PDF for entire categories automatically when changed or on demand for any number of songs. Scheduling is done via [Huey](https://github.com/coleifer/huey) and generation itself uses [Weasyprint](https://github.com/Kozea/WeasyPrint).

### Local development

For enabling PDF generation for local development without having a separate worker, I recommend adding this line to `settings.py`:

```yaml
HUEY = {"immediate": True}
```

### Production development

For production, using separate worker is recommended as it does not block the main thread and subsequent request. You can configure it using Redis like this:

```yaml
pool = ConnectionPool(host="localhost", port=6379, max_connections=20, db=2)
HUEY = RedisHuey("default", connection_pool=pool)
```

You can run worker through `run_huey` manage command
```bash
make worker
```

### FAQ

1. `uv sync` throws 

       ERROR: Couldn't install package: rcssmin
       Package installation failed...

    Install `python3-dev` for Debian-based distro or `python3-devel` for RHEL-based distribution

