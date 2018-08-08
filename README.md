# Meetings Registration Tool

Online registration system for managing meeting participants and for printing badges or reports.

[![Travis](https://travis-ci.org/eaudeweb/meetings-registration-tool.svg?branch=master)](
https://travis-ci.org/eaudeweb/meetings-registration-tool)
[![Coverage](https://coveralls.io/repos/github/eaudeweb/meetings-registration-tool/badge.svg?branch=master)](https://coveralls.io/github/eaudeweb/meetings-registration-tool?branch=master)
[![Docker](https://dockerbuildbadges.quelltext.eu/status.svg?organization=eaudeweb&repository=mrt)](https://hub.docker.com/r/eaudeweb/mrt/builds)

## Installation

* Install `Docker <https://docker.com>`_
* Install `Docker Compose <https://docs.docker.com/compose>`_

1. Clone the repo::

        git clone https://github.com/eaudeweb/meetings-registration-tool.git
        cd meetings-registration-tool

1. Create configuration files and edit all the following files:

        cp settings.example settings.py
        cp .env.example .env
        cp docker/db.env.example docker/db.env
        cp docker/init.sql.example docker/init.sql
        cp docker/log.env.example docker/log.env
        cp docker/app.env.example docker/app.env

1. Create the docker-compose.override.yml, either by copying docker-compose.prod.yml or docker-compose.dev.yml:

        cp docker-compose.prod.yml docker-compose.override.yml

1. Spin up the docker containers:

        docker-compose up -d
        docker-compose ps

1. To clean printout jobs older than one month and delete the files, run this command (to keep the printout files remove the --hook parameter):

        docker exec mrt.rq python manage.py rq cleanup --hook clean_printouts

## Production deployment notes

The application needs an webserver in front to handle the requests.

### Apache conf

        <VirtualHost *:443>
                ProxyPreserveHost On
                RequestHeader set X-Forwarded-Proto "https"

                ProxyPass /static/files http://localhost:5001/static/files retry=2
                ProxyPass / http://localhost:5000/ retry=2
                ProxyPassReverse / http://localhost:5000/
        </VirtualHost>

### Nginx conf

        server {

        location /static/files {
                proxy_pass http://localhost:5001/static/files;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto "https";
        }

        location / {
                proxy_pass http://localhost:5000;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                client_max_body_size 30m;
                proxy_set_header X-Forwarded-Proto "https";
        }

## Upgrade

1. Upgrade repo::

        cd meetings-registration-tool
        git pull

1. Upgrade image tag::

        vim .env

1. Get the latest docker images and restart the docker containers::

        docker-compose pull
        docker-compose up -d
        docker-compose ps

## Logging

For production logging:

1. Update log.env with your Papertrail host and port destination values (<https://papertrailapp.com/account/destinations>):

        vim docker/log.env

For accurate _remote_addr_ values, please insert the correct header in VHOST file. See <https://stackoverflow.com/questions/45260132/docker-get-users-real-ip> for example.

1. Error logging is made with Sentry.io. Get client key from <https://sentry.io/[organisation]/[project]/settings/keys/> and set the value of SENTRY_DSN from settings.py file::

        SENTRY_DSN='<https://xxx@sentry.io/232313>'

Restart the application and run <http://app-url/crashme> to test the integration.

## Backup

To backup the application run the following commands:

        docker exec mrt.db pg_dump -Upostgres <db_name> -Cc | gzip  > db.sql.gz
        docker exec mrt.app tar cvf - /var/local/meetings/instance/files/ | gzip > files.gz

-Cc is equivalent to --create --clean.

    `--create` tells pg_dump to include tables, views, and functions in the backup, not just the data contained in the tables.
    `--clean` tells pg_dump to start the SQL script by dropping the data that is currently in the database. This makes it easier to restore in one step.

## Data migration

1. Database

Copy the Postgres SQL dump file inside the postgres container, drop the current database and use psql to import the backup (you will find the POSTGRES_DBUSER and the POSTGRES_PASSWORD in the system environment variables)::

    $ docker cp backup.sql mrt.db:/tmp/backup.sql
    $ docker exec -it mrt.db bash
    /# dropdb <db>;
    /# createdb <db>;
    /# psql < /tmp/backup.sql

1. Files

Copy the _files_ directory to the _mrt.app_ container, under the _instance_ directory:

    $ sudo docker cp ./files mrt.app:/var/local/meetings/instance/
    $ sudo docker exec -ti mrt.app bash
    # chown root:root /var/local/meetings/instance/files

## Running unit tests

Simply run py.test testsuite, it will find and run the tests. For a bit of speedup you can install pytest-xdist and run tests in parallel, py.test testsuite -n 4.

## Create a migration after changes in models.py

Simply run the next commands in the application container:

        python manage.py alembic revision -- --autogenerate -m 'commit message'
        python manage.py alembic upgrade head

## i18n deployment on development

Run the pybabel command that comes with Babel to extract your strings:

        pybabel extract -F mrt/babel.cfg -k lazy_gettext -o mrt/translations/messages.pot mrt/

Create translations:

        pybabel init -i mrt/translations/messages.pot -d mrt/translations -l es
        pybabel init -i mrt/translations/messages.pot -d mrt/translations -l fr

To compile the translations for use, pybabel helps again:

        pybabel compile -d mrt/translations

Merge the changes:

        pybabel update -i mrt/translations/messages.pot -d mrt/translations

## Use the UN official list of countries

By default, the list of countries used in country selection fields is the one supplied by the babel package (which in turn gets the data from CLDR). If you want to switch to the UN official list of countries, you can do so by running the command:

        python manage.py countries_un

Running this command is a one-time step. The list of countries is extracted from the excel file mrt/static/localedata/countries_un.xslx and based on the information parsed, the data files used by babel are partially overwritten. Since running the command modifies the files used by babel, the only way to restore the default list is to restore those data files (which can be done by reinstalling the babel package, for example).

If the babel package is updated, the command will have to be run again, to modify the newly added locale data files.

## Integration in CMS pages

Simply insert the snippet bellow in the CMS page:

        <div style="width: 100%; height: 2500px; overflow: hidden; position: relative;">
                <iframe scrolling="no" src="<registration-url>" style="left: -50px; top: -180px; width: 105%; height: 2700px; position: absolute;"></iframe>
        </div>

The registration URL can be copied from Meeting -> Settings -> Overview -> Participant registration form.
