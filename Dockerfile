# VERSION 0.1.3

# USAGE

FROM      ubuntu:14.04.4
MAINTAINER V. David Zvenyach <vladlen.zvenyach@gsa.gov>

###
# Depenedencies
###

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
      nodejs \
      npm \
      python3-dev \
      python3-pip \
      unzip \
      wget \
      zlib1g-dev \

      # Preemptively install these so we don't have to clean up after RVM.
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

    # Clean up packages.
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

###
## Python

ENV PYENV_FILE v20160310.zip
ENV PYENV_ROOT /opt/pyenv

RUN wget https://github.com/yyuu/pyenv/archive/${PYENV_FILE} \
      --no-verbose \
  && unzip $PYENV_FILE -d $PYENV_ROOT \
  && mv $PYENV_ROOT/pyenv-20160310/* $PYENV_ROOT/ \
  && rm -r $PYENV_ROOT/pyenv-20160310

ENV PATH $PYENV_ROOT/bin:$PATH

RUN echo 'eval "$(pyenv init -)"' >> /etc/profile \
    && eval "$(pyenv init -)" \
    && pyenv install 2.7.11 \
    && pyenv install 3.5.0 \
    && pyenv local 3.5.0

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools
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
# Go

ENV GOLANG_VERSION 1.3.3

RUN curl -sSL https://golang.org/dl/go${GOLANG_VERSION}.src.tar.gz \
    | tar -v -C /usr/src -xz

RUN cd /usr/src/go/src \
      && ./make.bash --no-clean 2>&1

ENV PATH /usr/src/go/bin:$PATH
ENV GOPATH /go
ENV PATH /go/bin:$PATH

###
# Node
RUN ln -s /usr/bin/nodejs /usr/bin/node

###
# Installation
###

###
# ssllabs-scan

RUN mkdir -p /go/src /go/bin \
      && chmod -R 777 /go
RUN go get github.com/ssllabs/ssllabs-scan
RUN cd /go/src/github.com/ssllabs/ssllabs-scan/ \
      && git checkout stable \
      && go install
ENV SSLLABS_PATH /go/bin/ssllabs-scan

###
# phantomas

RUN npm install \
      --global \
    phantomas \
    phantomjs-prebuilt \
    es6-promise@3.1.2 \
    pa11y@3.0.1

###
# pshtt

RUN PYENV_VERSION=2.7.11 pyenv exec pip install pshtt
ENV PSHTT_PATH /opt/pyenv/versions/2.7.11/bin/pshtt

###
# Create Unprivileged User
###

ENV SCANNER_HOME /home/scanner
RUN mkdir $SCANNER_HOME

COPY . $SCANNER_HOME

###
# Uncomment the two instructions below to run pshtt scans using a modified trust
# store that includes the Federal Common Policy CA. This is useful for Federal
# agencies that are interested in seeing their pshtt status from the perspective
# of a client footprint that trusts FPKI.
###
#ENV REQUESTS_CA_BUNDLE=$SCANNER_HOME/ssl/requests_plus_fcpca.pem
#RUN echo $REQUESTS_CA_BUNDLE

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
