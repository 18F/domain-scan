# VERSION 0.1.3

# USAGE

FROM      ubuntu:14.04.4
MAINTAINER V. David Zvenyach <vladlen.zvenyach@gsa.gov>

###
# Depenedencies
###

RUN \
    # https://docs.docker.com/engine/installation/linux/ubuntulinux/#update-your-apt-sources
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
    && apt-get purge lxc-docker \

    && apt-get install \
        -qq \
        --yes \
        --no-install-recommends \
        --no-install-suggests \
      build-essential=11.6ubuntu6 \
      curl=7.35.0-1ubuntu2.6 \
      git \
      libc6-dev \
      libfontconfig1=2.11.0-0ubuntu4.1 \
      libreadline-dev=6.3-4ubuntu2 \
      libssl-dev \
      libssl-doc \
      libxml2-dev=2.9.1+dfsg1-3ubuntu4.7 \
      libxslt1-dev=1.1.28-2build1 \
      libyaml-dev=0.1.4-3ubuntu3.1 \
      nodejs=0.10.25~dfsg2-2ubuntu1 \
      npm=1.3.10~dfsg-1 \
      python3-dev=3.4.0-0ubuntu2 \
      python3-pip=1.5.4-1ubuntu3 \
      zlib1g-dev=1:1.2.8.dfsg-1ubuntu1 \

      # https://docs.docker.com/engine/installation/linux/ubuntulinux/
      apparmor \
      docker-engine \

      # Preemptively install these so we don't have to clean up after RVM.
      autoconf=2.69-6 \
      automake=1:1.14.1-2ubuntu1 \
      bison=2:3.0.2.dfsg-2 \
      gawk=1:4.0.1+dfsg-2.1ubuntu2 \
      libffi-dev=3.1~rc1+r3.0.13-12ubuntu0.1 \
      libgdbm-dev=1.8.3-12build1 \
      libncurses5-dev=5.9+20140118-1ubuntu1 \
      libsqlite3-dev=3.8.2-1ubuntu2.1 \
      libtool=2.4.2-1.7ubuntu1 \
      pkg-config=0.26-1ubuntu4 \
      sqlite3=3.8.2-1ubuntu2.1 \

      # Additional dependencies for python-build
      libbz2-dev \
      llvm \
      libncursesw5-dev \

    # Clean up packages.
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

###
# Ruby

# Get RVM.
RUN gpg --keyserver hkp://keys.gnupg.net --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3
RUN curl -sSL https://get.rvm.io | bash -s stable --ruby=2.1.5
RUN /bin/bash -l -c "rvm --default use 2.1.5"

# Install Bundler for each version of ruby
RUN /bin/bash -l -c "gem install bundler --no-ri --no-rdoc"
RUN /bin/bash -l -c "gem install site-inspector -v 1.0.2 --no-ri --no-rdoc"

###
# Node
RUN ln -s /usr/bin/nodejs /usr/bin/node

###
# Installation
###

###
# phantomas

RUN npm install \
      --silent \
      --global \
    phantomas

###
# Create Unprivileged User
###

ENV SCANNER_HOME /home/scanner
RUN mkdir $SCANNER_HOME

COPY . $SCANNER_HOME

RUN echo ". /usr/local/rvm/scripts/rvm" > $SCANNER_HOME/.bashrc

RUN groupadd -r scanner \
  && useradd -r -c "Scanner user" -g scanner scanner \
  && chown -R scanner:scanner ${SCANNER_HOME} \
  && usermod -a -G rvm scanner

###
# Prepare to Run
###

WORKDIR $SCANNER_HOME

# Volume mount for use with the 'data' option.
VOLUME /data

ENTRYPOINT ["./scan_wrap.sh"]
