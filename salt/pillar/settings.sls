db:
    engine: django.db.backends.postgresql_psycopg2
    name: mrt
    user: mrt
    pass: mrt
    host: localhost
    port: 5432

system:
    path: /var/local/mrt
    venv: /var/local/mrt/venv
    python: /var/local/mrt/venv/bin/python

app:
    domain: mrt.dev
    env: devel
    secret_key: secret

