FROM python:alpine
CMD [ "python", "-u", "run.py" ]
WORKDIR /src

ADD requirements.txt requirements.txt

RUN apk add --no-cache py3-gevent && \
    apk add --no-cache --virtual .build-deps build-base libffi-dev libmemcached-dev zlib-dev && \
    pip --no-cache install -r requirements.txt && \
    apk del .build-deps

ADD *.py ./