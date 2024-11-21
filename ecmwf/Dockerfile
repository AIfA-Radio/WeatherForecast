FROM ubuntu:22.04

RUN apt-get update; \
    apt-get -y upgrade; \
    apt-get -y install cron; \
    apt-get -y install python3

# requirements
COPY ./requirements.txt /app/requirements.txt
RUN apt-get -y install python3-pip; \
    pip install -r /app/requirements.txt; \
    rm -f /app/requirements.txt

# application and data directory
COPY src/ecmwf_download.py /app/ecmwf_download.py
RUN mkdir -p /app/data

# Copy and enable your CRON task
COPY ./mycron /etc/cron.d/mycron
RUN chmod 0744 /etc/cron.d/mycron
RUN crontab /etc/cron.d/mycron
# Create empty log (TAIL needs this)
RUN touch /var/log/cron.log

CMD ["cron", "&&", "tail", "-f", "/var/cron.log"]
