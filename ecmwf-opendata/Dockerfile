FROM ubuntu:22.04
# FROM python:3.10.15-slim

RUN apt-get update; \
    apt-get -y upgrade; \
    apt-get -y install cron; \
    apt-get -y install python3

# requirements
COPY ./requirements.txt /app/requirements.txt
RUN apt-get -y install --upgrade pip; \
    pip install -r /app/requirements.txt; \
    rm -f /app/requirements.txt

# application and data directory
COPY ./src/ecmwf_download.py /app/src/ecmwf_download.py
COPY ./data/parameter.json /app/data/parameter.json

# Copy and enable your CRON task
COPY ./mycron /etc/cron.d/mycron
RUN chmod 0744 /etc/cron.d/mycron
RUN crontab /etc/cron.d/mycron
# Create empty log (TAIL needs this)
RUN touch /var/log/cron.log

# CMD ["python3", "/app/src/ecmwf_download.py", "-e"]
CMD ["cron", "&&", "tail", "-f", "/var/cron.log"]