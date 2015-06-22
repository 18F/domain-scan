# VERSION 0.0.1

# USAGE

FROM      ubuntu:14.04
MAINTAINER V. David Zvenyach <vladlen.zvenyach@gsa.gov>

COPY . /tmp/
WORKDIR /tmp

RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install -r requirements.txt

# Install ruby
RUN apt-get update && apt-get install -y libc6-dev libssl-doc build-essential curl git zlib1g-dev libssl-dev libreadline-dev libyaml-dev libxml2-dev libxslt-dev
RUN apt-get clean

# Install rbenv and ruby-build
RUN git clone https://github.com/sstephenson/rbenv.git /tmp/.rbenv
RUN git clone https://github.com/sstephenson/ruby-build.git /tmp/.rbenv/plugins/ruby-build
RUN /bin/bash -l -c "/tmp/.rbenv/plugins/ruby-build/install.sh"
ENV PATH /tmp/.rbenv/bin:/root/.rbenv/versions/2.1.4/bin:$PATH

RUN echo 'eval "$(rbenv init -)"' >> /etc/profile.d/rbenv.sh # or /etc/profile
RUN echo 'eval "$(rbenv init -)"' >> .bashrc
RUN /bin/bash -l -c "rbenv install 2.1.4"
RUN /bin/bash -l -c "rbenv global 2.1.4"
RUN /bin/bash -l -c "rbenv rehash"
# Install Bundler for each version of ruby
RUN /bin/bash -l -c "gem install bundler"
RUN /bin/bash -l -c "gem install site-inspector -v 1.0.2"

# Install Go
RUN apt-get update && apt-get install -y \
		gcc libc6-dev make \
		--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

ENV GOLANG_VERSION 1.3.3

RUN curl -sSL https://golang.org/dl/go$GOLANG_VERSION.src.tar.gz \
		| tar -v -C /usr/src -xz

RUN cd /usr/src/go/src && ./make.bash --no-clean 2>&1

ENV PATH /usr/src/go/bin:$PATH

RUN mkdir -p /go/src /go/bin && chmod -R 777 /go
ENV GOPATH /go
ENV PATH /go/bin:$PATH
RUN go get github.com/ssllabs/ssllabs-scan

# Install Node and Phantomas
RUN apt-get update && apt-get install -y nodejs npm libfontconfig1
RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN npm install --global phantomas

ENTRYPOINT ["/tmp/scan"]
