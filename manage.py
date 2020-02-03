#!/usr/bin/env python

from click import CommandCollection
from mrt.app import create_app
from mrt.manager import cli as manager_cli
from contrib.importer import cli as importer_cli


app = create_app()


if __name__ == '__main__':
    cli = CommandCollection(sources=[manager_cli, importer_cli])
    cli(obj={'app': app})
