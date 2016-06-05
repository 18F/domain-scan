# VERSION 0.1.3

# USAGE

FROM python:3-onbuild
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
# Create Unprivileged User
###

RUN groupadd -r scanner \
  && useradd -r -c "Scanner user" -g scanner scanner \
  && chown -R scanner:scanner /usr/src/app

###
# Prepare to Run
###

# Volume mount for use with the 'data' option.
VOLUME /data

ENTRYPOINT ["./scan_wrap.sh"]
