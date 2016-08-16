#!/bin/bash
set -e

COMMANDS="add_verified_flag_mp alembic countries_un create_superuser create_user import meetings migrate_hint remove_missing_countries rq runserver shell update_representing compile_translations"

if [ -z "$POSTGRES_ADDR" ]; then
    POSTGRES_ADDR="postgres"
fi

while ! nc -z $POSTGRES_ADDR 5432; do
  echo "Waiting for PostgreSQL server at '$POSTGRES_ADDR' to accept connections..."
  sleep 3s
done

if [ ! -e .skip-db-init ]; then
  touch .skip-db-init
  echo "Running DB CMD: ./manage.py alembic upgrade head"
  python manage.py alembic upgrade head
fi

if [ -z "$1" ]; then
  exec waitress-serve --port 5000 manage:app
fi

if [[ "$1" == "--"* ]]; then
  exec waitress-serve "$@" manage:app
fi

if [[ $COMMANDS == *"$1"* ]]; then
  exec python manage.py "$@"
fi

exec "$@"
