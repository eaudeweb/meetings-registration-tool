meetings-registration-tool
==========================

.. contents ::

Project Name
------------
The Project Name is Meetings Registration Tool

Prerequisites - System packages
-------------------------------

These packages should be installed as superuser (root).

RedHat based systems
~~~~~~~~~~~~~~~~~~~~
Install these before setting up an environment::

    yum install postgresql-devel

Debian based systems
~~~~~~~~~~~~~~~~~~~~
Install these before setting up an environment::

    apt-get install -y python-setuptools python-dev python-virtualenv git \
    postgresql postgresql-contrib postgresql-server-dev \
    libxml2-dev libxslt1-dev redis-server libjpeg-dev


Install dependencies
--------------------
We should use Virtualenv for isolated environments. The following commands will
be run as an unprivileged user in the product directory::

1. Clone the repository::

    git clone git@github.com:eaudeweb/meetings-registration-tool.git
    
This will work only if you have your public key stored in _SSH keys_ list of a user that has access rights on the repository. You can also create a read-only copy of the project, by using the HTTPS URL::
    
    git clone https://github.com/eaudeweb/meetings-registration-tool.git

2. Create & activate a virtual environment::

    cd meetings-registration-tool

    virtualenv --no-site-packages sandbox
    echo '*' > sandbox/.gitignore
    source sandbox/bin/activate

3. Install dependencies::

    pip install -r requirements-dep.txt
    
\* Use `pip install -r requirements-dep.txt` in development.


4. Create a configuration file::

To set up a configuration file run the following commands and look in
settings.example for an settings example file::

    mkdir -p instance
    echo '*' >> instance/.gitignore
    touch instance/settings.py

Complete the PRODUCT_NAME and PRODUCT_TITLE settings.

Create a directory named 'logos' inside instance directory which is the
location for product logo images. Add to settings.py PRODUCT_LOGO and
PRODUCT_SIDE_LOGO filenames.

Set the ADMINISTRATOR_EMAIL in instance/settings.py representing the
administator email.

Set the DEFAULT_MAIL_SENDER variable in instance/settings.py.
Notifications, reset password tokens, activation emails will not be sent
unless this variable is set.

Set the GOOGLE_ANALYTICS_KEY in instance/settings.py example if you
want to enable the Google Analytics tracking.


5. Set up the PostgreSQL database::

    # Replace <your username> and <password> with your PostgreSQL credentials:
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

6. Start RQ workers by running (for printouts)::

    ./manage.py rq workers printouts


Configure wkhtmltopdf in virtualenv
-----------------------------------

Printouts work using `wkhtmltopdf 0.12.1`. Using another version may cause
problems in rendering pdfs.

If you don't have this version installed, add it to your virtualenv.

1. Go to http://download.gna.org/wkhtmltopdf/0.12/0.12.1/ and select the build
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


Set up a cron job for deletion of old printout files
----------------------------------------------------

Printout files older than one month are deleted by using a managing command::

        ./manage.py rq cleanup

In order for this command to work properly, the ``redis`` system package (not
the python package) version must be above ``2.8``, otherwise the command will
fail due to ``redis`` lacking ``EVALSHA``.

Printout files deletion should be set up as a cron job. Here is an example of
such a job set to run daily:

        0 0 * * * /path/to/virtualenv/python /path/to/package/manage.py rq cleanup &>/dev/null


Use the UN official list of countries
-------------------------------------

By default, the list of countries used in country selection fields is the one
supplied by the ``babel`` package (which in turn gets the data from CLDR). If you
want to switch to the UN official list of countries, you can do so by running
the command::

    ./manage.py countries_un

Running this command is a one-time step. The list of countries is extracted
from the excel file ``mrt/static/localedata/countries_un.xslx`` and based on the
information parsed, the data files used by ``babel`` are partially overwritten.
Since running the command modifies the files used by ``babel``, the only way to
restore the default list is to restore those data files (which can be done
by reinstalling the ``babel`` package, for example).

If the ``babel`` package is updated, the command will have to be run again, to
modify the newly added locale data files.


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

    pybabel extract -F mrt/babel.cfg -k lazy_gettext -o mrt/translations/messages.pot mrt/

Create translations::

    pybabel init -i mrt/translations/messages.pot -d mrt/translations -l es
    pybabel init -i mrt/translations/messages.pot -d mrt/translations -l fr

To compile the translations for use, pybabel helps again::

    pybabel compile -d mrt/translations

Merge the changes::

    pybabel update -i mrt/translations/messages.pot -d mrt/translations


Import meeting from old version
-------------------------------
Simply run the next commands::

    ./manage.py import <database> <meeting_id>

In order to get the participants photos you must complete the PHOTOS_BASE_URL in settings and run:
    ./manage.py import <database> <meeting_id> --with-photos


Contacts
========

People involved in this project are:

* Cornel Nitu (cornel.nitu at eaudeweb.ro)
* Alex Eftimie (alex.eftimie at eaudeweb.ro)
* Dragos Catarahia (dragos.catarahia at eaudeweb.ro)
