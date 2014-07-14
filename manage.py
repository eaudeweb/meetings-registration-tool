#!/usr/bin/env python

from mrt.app import create_app
from mrt.manager import cli


app = create_app()


if __name__ == '__main__':
    cli(obj={'app': app})
