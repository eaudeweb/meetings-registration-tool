#!/bin/sh

if [ "x$FLASK_MIGRATE" = 'xyes' ]; then
    python manage.py alembic upgrade head
fi

if [ "x$FLASK_CREATE_SUPERUSER" = "xyes" ]; then
  python manage.py create_superuser --email="$SUPERUSER_EMAIL" --password="$SUPERUSER_PASSWORD"
fi

if [ -z "$1" ]; then
  uwsgi uwsgi.ini
fi

exec python manage.py $@
