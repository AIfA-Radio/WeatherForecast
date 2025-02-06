FROM ubuntu:22.04

RUN apt-get update; \
    apt-get -y upgrade; \
    apt-get -y install cron; \
    apt-get -y install python3; \
    apt-get -y install git;

RUN git clone --depth 1 -b main https://github.com/ecmwf/multiurl app/multiurl

# requirements
COPY ./requirements.txt /app/requirements.txt
RUN apt-get -y install --upgrade pip; \
    pip install -r /app/requirements.txt; \
    rm -f /app/requirements.txt
RUN pip install /app/multiurl/

# application and data directory
COPY ./src/gfs_fc_*.py /app/src/
COPY ./data/parameter.json /app/data/parameter.json
COPY ./logs/ /app/logs/

# Copy and enable your CRON task
COPY ./mycron /etc/cron.d/mycron
RUN chmod 0644 /etc/cron.d/mycron
RUN crontab /etc/cron.d/mycron
# Create empty log (TAIL needs this)
RUN touch /var/log/cron.log

CMD ["cron", "&&", "tail", "-f", "/var/cron.log"]