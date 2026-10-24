# Songbook image: the entrypoint is make, the arguments are Makefile targets, e.g.
#   migrate prerender cache_clear export_static start    (web)
#   worker                                              (Huey worker)
# Build: make image
# Deployment with Podman quadlets is described in deploy/DEPLOY.md.
# Debian slim rather than Alpine on purpose: the PDF index is sorted with locale.strxfrm under cs_CZ.UTF-8, and
# musl has no locale collation, so on Alpine "Č" and "Š" would sort after "Z" and "Ch" would not follow "H".

FROM docker.io/library/python:3.14-slim-trixie AS base

# WeasyPrint needs Pango/HarfBuzz, PDF song sorting needs the cs/en collation locales
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core locales make \
    && sed -i -E 's/^# ((cs_CZ|en_US)\.UTF-8 UTF-8)/\1/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=chords.settings.container \
    MEDIA_ROOT=/srv/media \
    STATIC_EXPORT_DIR=/srv/static \
    SETTINGS=chords.settings.container \
    RUN= \
    XDG_CACHE_HOME=/tmp/.cache \
    LANG=C.UTF-8

WORKDIR /app


FROM base AS build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext brotli \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-install-project --group production

COPY . .

# Everything that needs no database is baked into the image
RUN SECRET_KEY=build-only make compilemessages collectstatic compress_static


FROM base

# Links the package on ghcr.io to the repository
LABEL org.opencontainers.image.source="https://github.com/pehala/song-book"

# Shown as the version in the menu; the image has no git to read it from
ARG BUILD_DATE=unknown
ARG BUILD_REVISION=unknown
ENV BUILD_DATE=$BUILD_DATE \
    BUILD_REVISION=$BUILD_REVISION

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app /app

# Any unprivileged UID works, nothing looks it up by name; the quadlets map it to the host user
USER 1001:1001

ENTRYPOINT ["make", "--no-print-directory"]
CMD ["start"]
