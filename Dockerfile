# VERSION 0.3.0

FROM ubuntu:16.04
MAINTAINER Shane Frasier <jeremy.frasier@trio.dhs.gov>

###
# Dependencies
###
ENV DEBIAN_FRONTEND=noninteractive

RUN \
    apt-get update \
        -qq \
    && apt-get install \
        -qq \
        --yes \
        --no-install-recommends \
        --no-install-suggests \
      apt-utils \
      build-essential \
      curl \
      git \
      libc6-dev \
      libfontconfig1 \
      libreadline-dev \
      libssl-dev \
      libssl-doc \
      libxml2-dev \
      libxslt1-dev \
      libyaml-dev \
      make \
      unzip \
      wget \
      zlib1g-dev \
      autoconf \
      automake \
      bison \
      gawk \
      libffi-dev \
      libgdbm-dev \
      libncurses5-dev \
      libsqlite3-dev \
      libtool \
      pkg-config \
      sqlite3 \
      # Additional dependencies for python-build
      libbz2-dev \
      llvm \
      libncursesw5-dev \
      # Additional dependencies for third-parties scanner
      nodejs \
      npm \
      # Additional dependencies for a11y scanner
      net-tools \
      # Chrome dependencies
      fonts-liberation \
      libappindicator3-1 \
      libasound2 \
      libatk-bridge2.0-0 \
      libgtk-3-0 \
      libnspr4 \
      libnss3 \
      libxss1 \
      libxtst6 \
      lsb-release \
      xdg-utils

RUN apt-get install -qq --yes locales && locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8

###
# Google Chrome
###
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb
# The third-parties scanner looks for an executable called chrome
RUN ln -s /usr/bin/google-chrome-stable /usr/bin/chrome

###
## Python
###
ENV PYENV_RELEASE=1.2.2 PYENV_PYTHON_VERSION=3.6.4 PYENV_ROOT=/opt/pyenv \
    PYENV_REPO=https://github.com/pyenv/pyenv

RUN wget ${PYENV_REPO}/archive/v${PYENV_RELEASE}.zip \
      --no-verbose \
    && unzip v$PYENV_RELEASE.zip -d $PYENV_ROOT \
    && mv $PYENV_ROOT/pyenv-$PYENV_RELEASE/* $PYENV_ROOT/ \
    && rm -r $PYENV_ROOT/pyenv-$PYENV_RELEASE

#
# Uncomment these lines if you just want to install python...
#
ENV PATH $PYENV_ROOT/bin:$PYENV_ROOT/versions/${PYENV_PYTHON_VERSION}/bin:$PATH
RUN echo 'eval "$(pyenv init -)"' >> /etc/profile \
    && eval "$(pyenv init -)" \
    && pyenv install $PYENV_PYTHON_VERSION \
    && pyenv local ${PYENV_PYTHON_VERSION}

#
# ...uncomment these lines if you want to also debug python code in GDB
#
# ENV PATH $PYENV_ROOT/bin:$PYENV_ROOT/versions/${PYENV_PYTHON_VERSION}-debug/bin:$PATH
# RUN echo 'eval "$(pyenv init -)"' >> /etc/profile \
#     && eval "$(pyenv init -)" \
#     && pyenv install --debug --keep $PYENV_PYTHON_VERSION \
#     && pyenv local ${PYENV_PYTHON_VERSION}-debug
# RUN ln -s /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/python-gdb.py \
#     /opt/pyenv/versions/${PYENV_PYTHON_VERSION}-debug/bin/python3.6-gdb.py \
#     && ln -s /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/python-gdb.py \
#     /opt/pyenv/versions/${PYENV_PYTHON_VERSION}-debug/bin/python3-gdb.py \
#     && ln -s /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/python-gdb.py \
#     /opt/pyenv/versions/${PYENV_PYTHON_VERSION}-debug/bin/python-gdb.py
# RUN apt-get -qq --yes --no-install-recommends --no-install-suggests install gdb
# RUN echo add-auto-load-safe-path \
#     /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/ \
#     >> etc/gdb/gdbinit

###
# Update pip and setuptools to the latest versions
###
RUN pip install --upgrade pip setuptools

###
# Node
###
# RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash
RUN apt-get install -y nodejs

###
## pa11y
###

RUN wget https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2 \
    && tar xvjf phantomjs-2.1.1-linux-x86_64.tar.bz2 -C /usr/local/share/ \
    && ln -s /usr/local/share/phantomjs-2.1.1-linux-x86_64/bin/phantomjs /usr/local/bin/
RUN npm install --global pa11y@4.13.2 --ignore-scripts

###
## third_parties
###

RUN npm install puppeteer

###
# Create unprivileged User
###
ENV SCANNER_HOME /home/scanner
RUN mkdir $SCANNER_HOME \
    && groupadd -r scanner \
    && useradd -r -c "Scanner user" -g scanner scanner \
    && chown -R scanner:scanner ${SCANNER_HOME}

###
# Prepare to Run
###
WORKDIR $SCANNER_HOME

# Volume mount for use with the 'data' option.
VOLUME /data

COPY . $SCANNER_HOME

###
# domain-scan
###
RUN pip install --upgrade \
    -r requirements.txt \
    -r requirements-gatherers.txt \
    -r requirements-scanners.txt

# Clean up aptitude stuff we no longer need
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["./scan_wrap.sh"]
