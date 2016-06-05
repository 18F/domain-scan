# VERSION 0.1.3

# USAGE

FROM python:3
MAINTAINER V. David Zvenyach <vladlen.zvenyach@gsa.gov>

###
# Docker
###

RUN \
    # https://docs.docker.com/engine/installation/linux/ubuntulinux/
    apt-get update \
        -qq \
    && apt-get install \
        -qq \
        --yes \
        --no-install-recommends \
        --no-install-suggests \
      apt-transport-https \
      ca-certificates \
    && apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D \
    && echo deb https://apt.dockerproject.org/repo ubuntu-trusty main > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
        -qq \
    && apt-get install \
        -qq \
        --yes \
        --no-install-recommends \
        --no-install-suggests \
      apparmor \
      docker-engine \

    # Clean up packages.
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

###
# Python dependencies

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

###
# Create Unprivileged User
###

ENV SCANNER_HOME /home/scanner
RUN mkdir $SCANNER_HOME

COPY . $SCANNER_HOME

RUN groupadd -r scanner \
  && useradd -r -c "Scanner user" -g scanner scanner \
  && chown -R scanner:scanner ${SCANNER_HOME}

###
# Prepare to Run
###

WORKDIR $SCANNER_HOME

# Volume mount for use with the 'data' option.
VOLUME /data

ENTRYPOINT ["./scan_wrap.sh"]
