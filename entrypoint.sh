#!/bin/sh
set -e

# wait for Postgres
if [ "$DATABASE" != "sqlite" ]; then
  echo "Waiting for postgres..."
  until python -c "import psycopg2; conn = psycopg2.connect('dbname=${POSTGRES_DB} user=${POSTGRES_USER} password=${POSTGRES_PASSWORD} host=${POSTGRES_HOST} port=${POSTGRES_PORT}'); conn.close()"; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
  done
fi

# migrate and collectstatic only in dev via override; in prod you can run manually
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
