meetings-registration-tool
==========================

.. contents ::

Project Name
------------
The Project Name is Meetings Registration Tool

Prerequisites - System packages
-------------------------------

These packages should be installed as superuser (root).

Debian based systems
~~~~~~~~~~~~~~~~~~~~
Install these before setting up an environment::

    apt-get install python-setuptools python-dev python-virtualenv git \
    postgresql-9.1 postgresql-contrib-9.1 postgresql-server-dev-9.1


Install dependencies
--------------------
We should use Virtualenv for isolated environments. The following commands will
be run as an unprivileged user in the product directory::

1. Clone the repository::

    git clone git@github.com:eaudeweb/meetings-registration-tool.git

2. Create & activate a virtual environment::

    virtualenv --no-site-packages sandbox
    echo '*' > sandbox/.gitignore
    source sandbox/bin/activate

3. Install dependencies::

    pip install -r requirements-dev.txt


4. Create a configuration file::

To set up a configuration file run the following commands and look in
settings.example for an settings example file::

    mkdir -p instance
    echo '*' >> instance/.gitignore
    touch instance/settings.py


5. Set up the PostgreSQL database::
    # Replace [your username] and [password] with your MySQL credentials:
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

After that, run alembic upgrade to have the tables created::

    ./manage.py alembic upgrade head


Development hints
=================

Requirements
------------

User ``requirements-dev.txt``::

    pip install -r requirements-dev.txt


Running unit tests
------------------

Simply run ``py.test testsuite``, it will find and run the tests. For a
bit of speedup you can install ``pytest-xdist`` and run tests in
parallel, ``py.test testsuite -n 4``.


Create a migration after changes in models.py::
---------------------------------------------

    ./manage.py alembic revision -- --autogenerate -m 'commit message'
    ./manage.py alembic upgrade head


Create a user
-------------

To create a user run the following command::

    ./manage.py create_user


Setup Git Pre-Commit Lint
-------------------------

Lint python files on commit::

    echo 'git lint' > .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit


Contacts
========

People involved in this project are:

* Cornel Nitu (cornel.nitu at eaudeweb.ro)
* Alex Eftimie (alex.eftimie at eaudeweb.ro)
* Dragos Catarahia (dragos.catarahia at eaudeweb.ro)
