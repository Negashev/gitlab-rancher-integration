FROM python:alpine

WORKDIR /src

ADD requirements.txt requirements.txt

RUN apk add --no-cache py3-gevent libpq mariadb-connector-c-dev && \
    apk add --no-cache --virtual .build-deps build-base libffi-dev libmemcached-dev zlib-dev postgresql-dev mariadb-dev && \
    pip --no-cache install -r requirements.txt && \
    apk del .build-deps

ENV SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@database/gri \
    SQLALCHEMY_ECHO=0 \ 
    DRAMATIQ_BROKER=redis://queue:6379

CMD gunicorn \
  --bind 0.0.0.0:443 \
  --certfile /etc/webhook/certs/server.crt --keyfile /etc/webhook/certs/server.key \
  run:app

ADD *.py ./