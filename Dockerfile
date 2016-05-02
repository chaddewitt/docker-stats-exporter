FROM python:2.7
MAINTAINER  Chad Dewitt <projectaur@gmail.com>

COPY requirements.txt /opt/requirements.txt
WORKDIR /opt
RUN pip install -r requirements.txt
COPY src /opt/src

EXPOSE      8081
ENTRYPOINT  ["uwsgi", \
             "--http", "0.0.0.0:8081", \
             "--module", "src.application", \
             "--callable", "app", \
             "--need-app"]
