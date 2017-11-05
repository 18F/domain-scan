# VERSION 0.3.0

# USAGE

FROM      ubuntu:16.04
MAINTAINER V. David Zvenyach <vladlen.zvenyach@gsa.gov>

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
      # Not sure what these dependencies are for
      nodejs \
      npm

###
## Python
###
ENV PYENV_RELEASE=1.1.1 PYENV_PYTHON_VERSION=3.6.1 PYENV_ROOT=/opt/pyenv \
    PYENV_REPO=https://github.com/pyenv/pyenv

RUN wget ${PYENV_REPO}/archive/v${PYENV_RELEASE}.zip \
      --no-verbose \
    && unzip v$PYENV_RELEASE.zip -d $PYENV_ROOT \
    && mv $PYENV_ROOT/pyenv-$PYENV_RELEASE/* $PYENV_ROOT/ \
    && rm -r $PYENV_ROOT/pyenv-$PYENV_RELEASE

#
# Uncomment these lines if you just want to install python...
#
# ENV PATH $PYENV_ROOT/bin:$PYENV_ROOT/versions/${PYENV_PYTHON_VERSION}/bin:$PATH
# RUN echo 'eval "$(pyenv init -)"' >> /etc/profile \
#     && eval "$(pyenv init -)" \
#     && pyenv install $PYENV_PYTHON_VERSION \
#     && pyenv local ${PYENV_PYTHON_VERSION}

#
# ...uncomment these lines if you want to also debug python code in GDB
#
ENV PATH $PYENV_ROOT/bin:$PYENV_ROOT/versions/${PYENV_PYTHON_VERSION}-debug/bin:$PATH
RUN echo 'eval "$(pyenv init -)"' >> /etc/profile \
    && eval "$(pyenv init -)" \
    && pyenv install --debug --keep $PYENV_PYTHON_VERSION \
    && pyenv local ${PYENV_PYTHON_VERSION}-debug
RUN ln -s /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/python-gdb.py \
    /opt/pyenv/versions/${PYENV_PYTHON_VERSION}-debug/bin/python3.6-gdb.py \
    && ln -s /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/python-gdb.py \
    /opt/pyenv/versions/${PYENV_PYTHON_VERSION}-debug/bin/python3-gdb.py \
    && ln -s /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/python-gdb.py \
    /opt/pyenv/versions/${PYENV_PYTHON_VERSION}-debug/bin/python-gdb.py
RUN apt-get -qq --yes --no-install-recommends --no-install-suggests install gdb
RUN echo add-auto-load-safe-path \
    /opt/pyenv/sources/${PYENV_PYTHON_VERSION}-debug/Python-${PYENV_PYTHON_VERSION}/ \
    >> etc/gdb/gdbinit

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip \
    && pip3 install --upgrade setuptools \
    && pip3 install -r requirements.txt

###
# Go
###
ENV GOLANG_VERSION=1.8.3 PATH=/go/bin:/usr/src/go/bin:$PATH GOPATH=/go \
    GOROOT=/usr/src/go

RUN curl -sSL https://storage.googleapis.com/golang/go${GOLANG_VERSION}.linux-amd64.tar.gz \
    | tar -v -C /usr/src -xz

###
# Node
###
RUN ln -s /usr/bin/nodejs /usr/bin/node

###
# phantomas
###
RUN npm install --global phantomas phantomjs-prebuilt \
    es6-promise@3.1.2 pa11y@3.0.1

###
# pshtt
###
RUN apt-get install -qq --yes locales && locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8
RUN pip3 install pshtt


###
# Create unprivileged User
###
ENV SCANNER_HOME /home/scanner
RUN mkdir $SCANNER_HOME \
    && groupadd -r scanner \
    &&  useradd -r -c "Scanner user" -g scanner scanner \
    && chown -R scanner:scanner ${SCANNER_HOME}


###
# Prepare to Run
###
WORKDIR $SCANNER_HOME

# Volume mount for use with the 'data' option.
VOLUME /data

ENTRYPOINT ["./scan_wrap.sh"]

# Clean up aptitude stuff we no longer need
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . $SCANNER_HOME
