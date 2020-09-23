FROM python:alpine
CMD [ "python", "-u", "run.py" ]
WORKDIR /src
RUN apk add --update py3-yaml
ADD requirements.txt requirements.txt
RUN pip --no-cache install -r requirements.txt
ADD *.py ./