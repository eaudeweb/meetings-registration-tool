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
    postgresql-9.1 postgresql-contrib-9.1 postgresql-server-dev-9.1 \
    libxml2-dev libxslt1-dev redis-server


Install dependencies
--------------------
We should use Virtualenv for isolated environments. The following commands will
be run as an unprivileged user in the product directory::

1. Clone the repository::

    git clone git@github.com:eaudeweb/meetings-registration-tool.git

2. Create & activate a virtual environment::

    cd meetings-registration-tool

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

.. Create a directory named 'logos' inside instance directory which is the
.. location for product logo images. Add to settings.py PRODUCT_LOGO and
.. PRODUCT_SIDE_LOGO filenames.


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

    ./manage.py alembic upgrade head\

6. Start RQ workers by running (for printouts):

    ./manage.py rq workers printouts


Configure wkhtmltopdf in virtualenv
-----------------------------------

Printouts work using `wkhtmltopdf 0.12.1`. Using another version may cause
problems in rendering pdfs.

If you don't have this version installed, add it to your virtualenv.

1. Go to http://sourceforge.net/projects/wkhtmltopdf/files/0.12.1/ and select the build
   corresponding with your system. Copy the direct link into your clipboard

2. Install it locally in your virtualenv
    
    * For RedHat-based systems in production::

         wget $PASTE_URL_COPIED_AT_STEP_1
         # $PACKAGE is the file downloaded with wget
         sudo rpm -i --prefix=/var/local/wkhtmltox-0.12.1 $PACKAGE.rpm
         # If the command fails because the file is already installed
         # copy `wkhtmltopdf` from the installation directory and skip
         # the next command
         cp /var/local/wkhtmltox-0.12.1/bin/wkhmtltopdf sandbox/bin/

    * For RedHat-based development systems::

         # If you don't work on projects that require other versions
         # Install this version globally
         wget $PASTE_URL_COPIED_AT_STEP_1
         sudo rpm -i $PACKAGE.rpm

    * For Debian based systems::

         wget $PASTE_URL_COPIED_AT_STEP_1
         dpkg-deb -x wkhtmltox-0.12.1_<your_distro>.deb sandbox
         cp sandbox/usr/local/bin/wkhtmltopdf sandbox/bin


Development hints
=================

Requirements
------------

User ``requirements-dev.txt``::

    pip install -r requirements-dev.txt


Configure deploy
----------------

- copy ``fabfile/env.ini.example`` to ``fabfile/env.ini``
- configure staging and production settings
- run ``fab staging deploy`` or ``fab production deploy``

To clean printout jobs older than one month and delete the files,
run this command::

    ./manage.py rq cleanup --hook clean_printouts

To keep the printout files remove the `--hook` parameter


Running unit tests
------------------

Simply run ``py.test testsuite``, it will find and run the tests. For a
bit of speedup you can install ``pytest-xdist`` and run tests in
parallel, ``py.test testsuite -n 4``.


Create a migration after changes in models.py
---------------------------------------------
Simply run the next commands::

    ./manage.py alembic revision -- --autogenerate -m 'commit message'
    ./manage.py alembic upgrade head


Create a user
-------------

To create a user run the following command::

    ./manage.py create_user

To create a superuser, use::

    ./manage.py create_superuser


Setup Git Pre-Commit Lint
-------------------------

Lint python files on commit::

    echo 'git lint' > .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit


i18n deployment
---------------

Run the `pybabel` command that comes with Babel to extract your strings::
    pybabel extract -F mrt/babel.cfg -o mrt/translations/messages.pot .

Create translations::
    pybabel init -i mrt/translations/messages.pot -d cites/translations -l es
    pybabel init -i mrt/translations/messages.pot -d cites/translations -l fr

To compile the translations for use, pybabel helps again::
    pybabel compile -d mrt/translations

Merge the changes::
    pybabel update -i mrt/translations/messages.pot -d mrt/translations


Contacts
========

People involved in this project are:

* Cornel Nitu (cornel.nitu at eaudeweb.ro)
* Alex Eftimie (alex.eftimie at eaudeweb.ro)
* Dragos Catarahia (dragos.catarahia at eaudeweb.ro)
