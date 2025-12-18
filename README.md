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

* Override any setting you want in `chords/settings/production.py`
  * Set `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` to actual domain you want the site to exist on
  * Generate `SECRET_KEY` unique for this site (https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-SECRET_KEY)
  * Override both `CACHES` and `DATABASES` to point to your Redis and PostgreSQL (or other DB engine) respectively
  * Set `TENANT_HOSTNAME` to the hostname that the site should use
* Setup gunicorn or any other WSGI server
* Setup Worker
  * `uv run python manage.py run_huey --worker-type process`
  * Responsible for async PDF generation
* Setup NGINX or any other reverse proxy to expose the website

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

