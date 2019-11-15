FROM python:2.7-slim

ARG REQUIREMENTS_FILE=requirements-dep.txt

ENV APP_HOME=/var/local/meetings/

# libssl1.0-dev => https://stackoverflow.com/questions/42094214/why-is-qsslsocket-working-with-qt-5-3-but-not-qt-5-7-on-debian-stretch?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
# libpcre3 libpcre3-dev => uwsgi
# libpng-dev fails to install see https://github.com/tcoopman/image-webpack-loader/issues/95
RUN runDeps="curl vim build-essential libssl-dev libpq-dev libxml2-dev libxslt1-dev libjpeg-dev libxrender1 libfontconfig libxtst6 libpcre3 libpcre3-dev" \
    && apt-get update \
    && apt-get install -y --no-install-recommends $runDeps \
    && curl -o /tmp/wkhtmltopdf.tgz -sL https://svn.eionet.europa.eu/repositories/Zope/trunk/wk/wkhtmltopdf-0.12.2.4.tgz  \
    && tar -zxvf /tmp/wkhtmltopdf.tgz -C /tmp/ \
    && mv -v /tmp/wkhtmltopdf /usr/bin/ \
    && curl -o /tmp/libpng12.deb -sL http://mirrors.kernel.org/ubuntu/pool/main/libp/libpng/libpng12-0_1.2.54-1ubuntu1_amd64.deb \
    && dpkg -i /tmp/libpng12.deb \
    && rm /tmp/libpng12.deb \
    && apt-get clean \
    && rm -vrf /var/lib/apt/lists/* \
    && rm -vrf /tmp/*

COPY requirements.txt $REQUIREMENTS_FILE $APP_HOME
WORKDIR $APP_HOME

RUN pip install --no-cache-dir -r $REQUIREMENTS_FILE \
    && mkdir -p $APP_HOME/instance/files

COPY . $APP_HOME

RUN pybabel compile -d mrt/translations \
    && mv settings.example instance/settings.py \
    && mv ./docker/docker-entrypoint.sh /bin/

ENTRYPOINT ["docker-entrypoint.sh"]
