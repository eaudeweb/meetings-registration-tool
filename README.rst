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

2. Customize deployment via setup.py::

   $ cp settings.example settings.py
   $ vim settings.py

2. Start application stack::

    $ docker-compose up -d
    $ docker-compose logs

3. Create super-user to login with::

    $ docker-compose run mrt create_superuser

4. See it in action:

    http://localhost


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


Contacts
========

People involved in this project are:

* Cornel Nitu (cornel.nitu at eaudeweb.ro)
* Iulia Chiriac (iulia.chiriac at eaudeweb.ro)

