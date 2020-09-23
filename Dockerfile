FROM python:alpine
CMD [ "python", "-u", "run.py" ]
WORKDIR /src
ADD requirements.txt requirements.txt
RUN pip --no-cache install -r requirements.txt
ADD *.py ./