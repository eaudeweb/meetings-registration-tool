#!/bin/sh

if [ -z "$POSTGRES_HOST" ]; then
  export POSTGRES_HOST="db"
fi

while ! nc -z ${POSTGRES_HOST} 5432; do
  echo "Waiting for Postgres server at '$POSTGRES_HOST' to accept connections on port 5432..."
  sleep 1s
done

if [ -z "$REDIS_HOST" ]; then
  export REDIS_HOST="redis"
fi

while ! nc -z ${REDIS_HOST} 6379; do
  echo "Waiting for Redis server at '$REDIS_HOST' to accept connections on port 6379..."
  sleep 1s
done


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
