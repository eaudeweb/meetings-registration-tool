python:
    pkg:
        - installed
        - names:
            - python-dev
            - python

nfs-kernel-server:
    pkg:
        - installed
        - names:
            - nfs-kernel-server

pip:
    pkg:
        - installed
        - name: python-pip
        - require:
            - pkg: python

virtualenv:
    pip:
        - installed
        - name: virtualenv
        - upgrade: true
        - bin_env: /usr/bin/pip
        - require:
            - pkg: python
            - pkg: pip

libjpeg-dev:
    pkg.installed:
        - name: libjpeg-dev

python-lxml-dev:
    pkg.installed:
        - names:
            - libxml2-dev
            - libxslt1-dev

python-cffi:
    pkg.installed:
        - name: libffi-dev

cairo:
    pkg.installed:
        - names:
            - python-cairosvg
            - libpango1.0-0

gettext:
    pkg.installed:
        - name: gettext

ro_locale:
  locale.present:
    - name: ro_RO.UTF-8

git:
    pkg.installed:
        - name: git

redis:
    pkg.installed:
        - name: redis-server

libxml2:
    pkg.installed:
        - name: libxml2-dev
