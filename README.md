meetings-registration-tool
==========================


Install dependencies
--------------------
We should use Virtualenv for isolated environments. The following commands will
be run as an unprivileged user in the product directory::

Clone the repository::

    git clone git@github.com:eaudeweb/meetings-registration-tool.git

Create & activate a virtual environment::

    virtualenv --no-site-packages sandbox
    echo '*' > sandbox/.gitignore
    source sandbox/bin/activate

Install dependencies::

    pip install -r requirements-dev.txt


Create a configuration file
---------------------------

To set up a configuration file run the following commands and look in
settings.example for an settings example file::

    mkdir -p instance
    touch instance/settings.py


Create database
-------------------------

To set up the PostgreSQL database in Debian, you need to install the
packages `postgresql-9.1`, `postgresql-contrib-9.1` and
`postgresql-server-dev-9.1`. Then create a database, enable the `hstore`
extension, and grant access to your user::

    root # su - postgres
    postgres $ psql
    psql (9.1.2)
    Type "help" for help.

    postgres=#  CREATE USER <your username> WITH PASSWORD '<password>';
    CREATE ROLE
    postgres=#  CREATE DATABASE meetings;
    CREATE DATABASE
    postgres=# GRANT ALL PRIVILEGES ON DATABASE meetings TO <your username>;
    GRANT
    postgres=# \q


Create a migration after changes in models.py
---------------------------------------------

    ./manage.py alembic revision -- --autogenerate -m 'commit message'
    ./manage.py alembic upgrade head


Setup Git Pre-Commit Lint
-------------------------

Lint python files on commit::

    echo 'git lint' > .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
