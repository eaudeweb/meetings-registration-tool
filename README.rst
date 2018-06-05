Meetings Registration Tool
==========================

.. contents ::

Installation
------------

* Install `Docker <https://docker.com>`_
* Install `Docker Compose <https://docs.docker.com/compose>`_

Usage
-----

1. Clone the repository::

    $ git clone https://github.com/eaudeweb/meetings-registration-tool.git
    $ cd meetings-registration-tool

2. Customize deployment via settings.py::

   $ cp settings.example settings.py
   $ vim settings.py

   Edit `DOMAIN_NAME` to include you domain name. E.g. https://meetings.cites.org

3. Customize env files::

    $ cp docker/postgres.env.example docker/postgres.env
    $ vim docker/postgres.env
    $ cp docker/init.sql.example docker/init.sql
    $ vim docker/init.sql
    $ cp docker/log.env.example docker/log.env
    $ vim docker/log.env
    $ cp docker/app.env.example docker/app.env
    $ vim docker/app.env

4. Start application stack::

    $ docker-compose up -d
    $ docker-compose logs

\* If your ``postgres`` container throws this error ``FATAL:  could not map anonymous shared memory: Cannot allocate memory``, add the following lines to ``docker-compose.yml`` > ``postgres`` > ``environment``::

    - POSTGRES_CONFIG_max_connections=10
    - POSTGRES_CONFIG_shared_buffers=512MB

5. Create super-user to login with::

    $ docker-compose run mrt create_superuser

6. See it in action::

    http://localhost:5000


Upgrade
-------

1. Get the latest source code::

    $ cd meetings-registration-tool
    $ git pull

2. Get the latest docker images::

    $ docker-compose pull

3. Restart application stack::

    $ docker-compose up -d

4. Check that everything is up-and-running::

   $ docker-compose ps

5. See the logs::

   $ docker-compose logs


Logging
-------

For production logging:

1. Update log.env with your Papertrail host and port destination values (https://papertrailapp.com/account/destinations)::

    $ vim docker/log.env

For accurate _remote_addr_ values, please insert the correct header in VHOST file. See https://stackoverflow.com/questions/45260132/docker-get-users-real-ip for example.

2. Error logging is made with Sentry.io. Get client key from https://sentry.io/[organisation]/[project]/settings/keys/ and set the value of SENTRY_DSN from settings.py file::

    SENTRY_DSN='https://xxx@sentry.io/232313'

Restart the application and run http://localhost:5000/crashme to test the integration.


Backup
------

To backup the application run the following commands:

    $ docker exec mrt.db pg_dump -Upostgres <db_name> -Cc | gzip  > db.sql.gz
    $ docker exec mrt.app tar cvf - /var/local/meetings/instance/files/ | gzip --rsyncable > files.gz

-Cc is equivalent to --create --clean.

    --create tells pg_dump to include tables, views, and functions in the backup, not just the data contained in the tables.
    --clean tells pg_dump to start the SQL script by dropping the data that is currently in the database. This makes it easier to restore in one step.

If you are using rsync.net or other incremental backup system, don't forget to add `--rsyncable` to gzip command.

Data migration
--------------

1. Database

Copy the Postgres SQL dump file inside the postgres container, drop the current database and use psql to import the backup (you will find the POSTGRES_DBUSER and the POSTGRES_PASSWORD in the system environment variables)::

    $ docker cp backup.sql mrt.db:/tmp/backup.sql
    $ docker exec -it mrt.db bash
    /# dropdb cms_meetings;
    /# createdb cms_meetings;
    /# psql < /tmp/backup.sql

2. Files

Copy the _files_ directory to the _mrt.app_ container, under the _instance_ directory:

    $ sudo docker cp ./files mrt.app:/var/local/meetings/instance/
    $ sudo docker exec -ti mrt.app bash
    # chown root:root /var/local/meetings/instance/files


Contacts
========

People involved in this project are:

* Cornel Nitu (cornel.nitu at eaudeweb.ro)
* Iulia Chiriac (iulia.chiriac at eaudeweb.ro)

