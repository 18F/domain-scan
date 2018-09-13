# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrant Docs: https://vagrantup.com

Vagrant.configure("2") do |config|
    config.vm.box = "ubuntu/bionic64"  # Ubuntu 18.04 x86_64

    config.vm.provision "shell", inline: <<-SHELL
        apt-get update
        apt-get install -y git python3 python3-pip python3-virtualenv python3-venv

        cd /vagrant

        pip3 install -U git+https://github.com/dhs-ncats/pshtt.git@develop git+https://github.com/dhs-ncats/trustymail.git@develop
        pip3 install -r requirements.txt

        echo "# Sample usage"
        echo "/vagrant/scan dhs.gov --scan=pshtt,trustymail,sslyze"
    SHELL
end
