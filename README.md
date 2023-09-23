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
  * `poetry run python manage.py rqworker default --with-scheduler`
  * Responsible for async PDF generation
* Setup NGINX or any other reverse proxy to expose the website

# Developing

## Dependencies

* Python 3.9+
* [gettext](https://www.gnu.org/software/gettext/)
    * Used for compiling locales
* [Redis](https://redis.io/)
    * Used as both cache and messaging queue for PDF generation

## Getting Started

First clone the repository from GitHub and switch to the new directory:

    git clone https://github.com/pehala/song-book.git
    cd song-book
    
Install pipenv and dependencies

    python -m pip install poetry
    poetry install 
    
Then simply initialize the website:

    make init

You can now run the development server:

    make run

### FAQ

1. `poetry install` throws 

       ERROR: Couldn't install package: rcssmin
       Package installation failed...

    Install `python3-dev` for Debian-based distro or `python3-devel` for RHEL-based distribution

