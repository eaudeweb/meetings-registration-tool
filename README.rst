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

    $ git clone git@github.com:eaudeweb/meetings-registration-tool.git
    $ cd meetings-registration-tool
    $ git checkout docker

2. Customize deployment via settings.py::

   $ cp settings.example settings.py
   $ vim settings.py

   Edit `DOMAIN_NAME` to include you domain name. E.g. https://meetings.cites.org
3. Customize env files::

    $ cp docker/postgres.env.example docker/postgres.env
    $ vim docker/postgres.env
    $ cp docker/log.env.example docker/log.env
    $ vim docker/log.env

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

1. Update log.env with your Papertrail credentials::

    $ vim docker/log.env

2. For accurate remote addr values, please insert the correct header in VHOST file.
See https://stackoverflow.com/questions/45260132/docker-get-users-real-ip for example.

Contacts
========

People involved in this project are:

* Cornel Nitu (cornel.nitu at eaudeweb.ro)
* Iulia Chiriac (iulia.chiriac at eaudeweb.ro)

