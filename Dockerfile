FROM python:2.7-slim
MAINTAINER "Eau de Web" <cornel.nitu@eaudeweb.ro>

ENV MRT_SRC=/var/local/meetings

RUN runDeps="curl vim build-essential netcat libpq-dev libxml2-dev libxslt1-dev libjpeg-dev libxrender1 libfontconfig libxtst6" \
 && apt-get update \
 && apt-get install -y --no-install-recommends $runDeps \
 && curl -o /tmp/wkhtmltopdf.tgz -SL https://svn.eionet.europa.eu/repositories/Zope/trunk/wk/wkhtmltopdf-0.12.2.4.tgz \
 && tar -zxvf /tmp/wkhtmltopdf.tgz -C /tmp/ \
 && mv -v /tmp/wkhtmltopdf /usr/bin/ \
 && rm -vrf /var/lib/apt/lists/* \
 && rm -vrf /tmp/*

COPY . $MRT_SRC/
WORKDIR $MRT_SRC

RUN pip install -r requirements-dep.txt \
 && pybabel compile -d mrt/translations \
 && mkdir -p $MRT_SRC/instance/files \
 && mkdir -p $MRT_SRC/instance/photos \
 && mkdir -p $MRT_SRC/instance/printouts \
 && mkdir -p $MRT_SRC/instance/badges \
 && mkdir -p $MRT_SRC/instance/user_index \
 && mkdir -p $MRT_SRC/instance/backgrounds \
 && mv settings.example instance/settings.py \
 && mv ./docker/docker-entrypoint.sh /bin/

ENTRYPOINT ["docker-entrypoint.sh"]
