FROM python:2.7-slim
MAINTAINER "Eau de Web" <cornel.nitu@eaudeweb.ro>

ENV MRT_SRC=/var/local/meetings

RUN runDeps="build-essential netcat libpq-dev libxml2-dev libxslt1-dev libjpeg-dev vim" \
 && apt-get update \
 && apt-get install -y --no-install-recommends $runDeps \
 && rm -rf /var/lib/apt/lists/*

COPY . $MRT_SRC/
WORKDIR $MRT_SRC

RUN pip install -r requirements-dep.txt \
 && mkdir -p $MRT_SRC/instance/files \
 && mv settings.example instance/settings.py \
 && mv docker-entrypoint.sh /bin/

ENTRYPOINT ["docker-entrypoint.sh"]
