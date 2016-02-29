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
      build-essential=11.6ubuntu6 \
      curl=7.35.0-1ubuntu2.6 \
      git=1:1.9.1-1ubuntu0.2 \
      libc6-dev=2.19-0ubuntu6.7 \
      libfontconfig1=2.11.0-0ubuntu4.1 \
      libreadline-dev=6.3-4ubuntu2 \
      libssl-dev=1.0.1f-1ubuntu2.17 \
      libssl-doc=1.0.1f-1ubuntu2.17 \
      libxml2-dev=2.9.1+dfsg1-3ubuntu4.7 \
      libxslt1-dev=1.1.28-2build1 \
      libyaml-dev=0.1.4-3ubuntu3.1 \
      make=3.81-8.2ubuntu3 \
      nodejs=0.10.25~dfsg2-2ubuntu1 \
      npm=1.3.10~dfsg-1 \
      python3-dev=3.4.0-0ubuntu2 \
      python3-pip=1.5.4-1ubuntu3 \
      unzip=6.0-9ubuntu1.5 \
      wget=1.15-1ubuntu1.14.04.1 \
      zlib1g-dev=1:1.2.8.dfsg-1ubuntu1 \

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

    # Clean up packages.
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

###
## Python

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
ENV SSLLABS_PATH /go/bin/ssllabs-scan

###
# phantomas

RUN npm install \
      --silent \
      --global \
    phantomas

###
# sslyze

ENV SSLYZE_VERSION 0.11
ENV SSLYZE_FILE sslyze-0_11-linux64.zip
ENV SSLYZE_DEST /opt

# Would be nice if bash string manipulation worked in ENV as this could use:
# ${SSLYZE_FILE%.*}
ENV SSLYZE_PATH ${SSLYZE_DEST}/sslyze-0_11-linux64/sslyze/sslyze.py
RUN wget https://github.com/nabla-c0d3/sslyze/releases/download/release-${SSLYZE_VERSION}/${SSLYZE_FILE} \
      --no-verbose \
  && unzip $SSLYZE_FILE -d $SSLYZE_DEST

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
