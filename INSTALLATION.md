# Installation of `domain-scan` #
This document discusses the installation and use of `domain-scan`.  In
some ways the instructions are slightly specific to the DHS NCATS BOD
18-01 scanning use case, but they are easily tailored.

## Installation options ##
When installing `domain-scan`, one has two options:
1. Install Docker on Linux, Windows, or OSX and run the tools via a
   Docker container.
2. Install the tools directly to a Linux host or VM.

## Installation via `docker` ##
### Prerequisites ###
A system with Docker installed.

### Installation ###
Pull down the Docker image that is unofficially published to the
[`dhsncats` account on Docker
Hub](https://hub.docker.com/u/dhsncats/dashboard/):
```
docker pull dhsncats/domain-scan:latest
```

This Docker image comes preinstalled with
[`dhs-ncats/pshtt`](https://github.com/dhs-ncats/pshtt),
[`dhs-ncats/trustymail`](https://github.com/dhs-ncats/trustymail),
[`nabla-c0d3/sslyze`](https://github.com/nabla-c0d3/sslyze/),
[`18F/domain-scan`](https://github.com/18F/domain-scan), and all of
their dependencies.  If you prefer, you can build the image from the
`Dockerfile` that is in the root directory of the
[`18F/domain-scan`](https://github.com/18F/domain-scan) project.

You should *always* run the `docker pull` command before using the
`dhsncats/domain-scan:latest` container, since updated versions of the
container will be published frequently to include any updates to
[`dhs-ncats/pshtt`], [`dhs-ncats/trustymail`], [`nabla-c0d3/sslyze`],
[`18F/domain-scan`], or their dependencies.

### Execution ###
Start the container with the arguments necessary to scan your domain(s):
```
docker run --volume $PWD/results:/home/scanner/results dhsncats/domain-scan:latest --scan=pshtt,trustymail,sslyze dhs.gov
```

Or, if for any reason you want to save the cache between runs:
```
docker run --volume $PWD/results:/home/scanner/results --volume $PWD/cache:/home/scanner/cache dhsncats/domain-scan:latest --scan=pshtt,trustymail,sslyze dhs.gov
```

## Installation in VM via Vagrant ##

### Prerequisites ###

1. [Vagrant](https://vagrantup.com)
2. `git`

### Installation ###

First, `cd` into your work directory and clone the `18F/domain-scan` repository:

```
cd /your/work/directory
git clone https://github.com/18F/domain-scan.git
cd domain-scan
```

Next, install Vagrant from: https://vagrantup.com

Use Vagrant to build a new VM with everything installed into it:

```
vagrant up
```

### Execution ###

To execute a scan against a domain, say `dhs.gov`, simply enter the VM and run
`/vagrant/scan ...`:

```
# SSH into the VM
vagrant ssh

# Run the scan
/vagrant/scan dhs.gov --scan=pshtt,trustymail,sslyze
```

When you are finished scanning, exit the virtual machine with `exit`.


## Installation directly to a Linux host ##
### Prerequisites ###
1. A Linux host or VM
2. `git`
3. `pyenv`

### Installation ###
First, `cd` into your work directory and clone the `18F/domain-scan` repository:
```
cd /your/work/directory
git clone https://github.com/18F/domain-scan.git
cd domain-scan
```

Next, install a recent version of Python and create a clean Python virtual environment:
```
pyenv install 3.6.4
pyenv local 3.6.4
python -m venv venv
source venv/bin/activate
```

Now install the latest versions of `dhs-ncats/trustymail` and
`dhs-ncats/pshtt`, then install the remaining `18F/domain-scan`
dependencies:
```
pip install --upgrade git+https://github.com/dhs-ncats/pshtt.git@develop git+https://github.com/dhs-ncats/trustymail.git@develop
pip install -r requirements.txt
```

Now exit the Python virtual environment and revert to the version of Python installed on your system:
```
deactivate
pyenv version system
```

### Execution ###
To execute a scan against a domain, say `dhs.gov`, simply reenter the
Python virtual environment and run `domain-scan`:
```
cd /your/work/directory/domain-scan
source venv/bin/activate
./scan dhs.gov --scan=pshtt,trustymail,sslyze
```

When you are finished scanning, exit the Python virtual environment
via the `deactivate` command.
