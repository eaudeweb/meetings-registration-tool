#!/usr/bin/env python

from meetings.app import create_app
from meetings.manager import cli


app = create_app()


if __name__ == '__main__':
    cli(obj={'app': app})
