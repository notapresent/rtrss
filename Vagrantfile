# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = "ubuntu/trusty64"

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  config.vm.network "forwarded_port", guest: 8080, host: 8080
  config.vm.network "forwarded_port", guest: 5432, host: 5432

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  config.vm.network "private_network", ip: "192.168.254.2"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  # config.vm.synced_folder "../data", "/vagrant_data"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  #
  config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
      # Customize the amount of memory on the VM:
      vb.memory = "1024"
  end
  #
  # View the documentation for the provider you are using for more
  # information on available options.

  # Define a Vagrant Push strategy for pushing to Atlas. Other push strategies
  # such as FTP and Heroku are also available. See the documentation at
  # https://docs.vagrantup.com/v2/push/atlas.html for more information.
  # config.push.define "atlas" do |push|
  #   push.app = "YOUR_ATLAS_USERNAME/YOUR_APPLICATION_NAME"
  # end

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.
  # config.vm.provision "shell", inline: <<-SHELL
  #   sudo apt-get update
  #   sudo apt-get install -y apache2
  # SHELL
    
# First provision script, must be run as root
$provision_root = <<SCRIPT
#!/bin/sh

echo "Setting up locale"
sudo locale-gen ru_RU.UTF-8
sudo dpkg-reconfigure locales

echo "Installing postgresql"
sudo apt-get update
sudo apt-get install -y postgresql postgresql-client

echo "Updating postgresql settings"
sudo sed -i 's/peer/trust/' /etc/postgresql/9.3/main/pg_hba.conf
echo '\nhost all all 192.168.254.0/24 md5' | sudo tee --append /etc/postgresql/9.3/main/pg_hba.conf
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/9.3/main/postgresql.conf 
sudo service postgresql restart

echo "Setting password for user postgres"
psql -Upostgres -c "ALTER USER postgres PASSWORD 'postgres';"

echo "Creating databases"
psql -Upostgres -c "CREATE DATABASE rtrss_dev TEMPLATE template0 ENCODING='UTF8';"
psql -Upostgres -c "CREATE DATABASE rtrss_test TEMPLATE template0 ENCODING='UTF8';"

echo "Installing pip"
curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo -H python2.7

echo "Installing virtualenvwrapper"
sudo -H pip install virtualenvwrapper
echo 'source /usr/local/bin/virtualenvwrapper_lazy.sh' >> /home/vagrant/.bashrc 

echo "Installing native package build requirements"
sudo apt-get install -y build-essential postgresql-server-dev-9.3 python-dev libxml2-dev libxslt1-dev libffi-dev

SCRIPT

# Second provision script, must be run as `vagrant` user
$provision_nonroot = <<SCRIPT
#!/bin/bash

cd /vagrant
source /usr/local/bin/virtualenvwrapper_lazy.sh
mkvirtualenv rtrss

echo "Installing dependencies"
pip install -r reqs/production.txt

echo "Installing development dependencies"
pip install -r reqs/development.txt

SCRIPT
    
    
  config.vm.provision "shell", inline: $provision_root
  config.vm.provision "shell", inline: $provision_nonroot, privileged: false
end
