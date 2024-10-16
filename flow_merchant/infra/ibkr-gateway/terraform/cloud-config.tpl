#!/bin/bash

set -euo pipefail

LOG_FILE="/var/log/ibkr-gateway-install.log"
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a $LOG_FILE
}

APPUSER=flowmerchant
APPGROUP=$APPUSER

SSH_PUB_KEY="${ssh_pub_key}"

log "Starting installation process"

# Create app user with sudo privileges
if ! getent group $APPGROUP > /dev/null; then
  log "Creating group $APPGROUP"
  groupadd $APPGROUP
fi

if ! id $APPUSER > /dev/null 2>&1; then
  log "Creating user $APPUSER"
  useradd -m -s /bin/bash -g $APPUSER $APPUSER
fi

# Add mailbriefly user to sudo list
log "Adding $APPUSER to sudoers"
echo "$APPUSER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$APPUSER
chmod 0440 /etc/sudoers.d/$APPUSER

log "Setting up SSH for $APPUSER"
mkdir -p /home/$APPUSER/.ssh
chmod 700 /home/$APPUSER/.ssh
echo $SSH_PUB_KEY >> /home/$APPUSER/.ssh/authorized_keys
chmod 600 /home/$APPUSER/.ssh/authorized_keys
chown -R $APPUSER:$APPGROUP /home/$APPUSER/.ssh

##
# Updates
apt-get update -y

##
# Install JAVA
##
log "Installing Java"
apt install -y default-jre
java -version

##
# Install Python
## 
log "Installing Python"
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

log "Getting Python 3.11.3"
wget https://www.python.org/ftp/python/3.11.3/Python-3.11.3.tgz
tar -xf Python-3.11.3.tgz
cd Python-3.11.3

log "Compiling Python 3.11.3"
./configure --enable-optimizations
make -j 12
make altinstall

log "Checking Python 3.11.3"
python3 --version

##
# Install gateway
##
log "Installing gateway"

log "Creating gateway service etc dir"
mkdir /etc/ibkr_gateway
chown -R $APPUSER:$APPGROUP /etc/ibkr_gateway
chmod 755 /etc/ibkr_gateway
echo '${ibkr_gateway_env_file}' > /etc/ibkr_gateway/.env
chmod 644 /etc/ibkr_gateway/.env

log "Creating gateway service file"
echo '${ibkr_gateway_service_file}' > /etc/systemd/system/ibkr_gateway.service
chmod 644 /etc/systemd/system/ibkr_gateway.service

log "Emplacing python gateway service files"
mkdir /usr/local/bin/ibkr_gateway
echo '${ibkr_gateway_main_py}' > /usr/local/bin/ibkr_gateway/main.py
echo '${ibkr_gateway_server_py}' > /usr/local/bin/ibkr_gateway/server.py
echo '${ibkr_gateway_config_py}' > /usr/local/bin/ibkr_gateway/config.py
echo '${ibkr_gateway_requirements_txt}' > /usr/local/bin/ibkr_gateway/requirements.txt
chown -R $APPUSER:$APPGROUP /usr/local/bin/ibkr_gateway
chmod 755 /usr/local/bin/ibkr_gateway/*

log "Enabling gateway service"
systemctl daemon-reload
systemctl enable ibkr_gateway.service
systemctl start myapp.service

##
# digital ocean has a bug that causes systemd-journald to fail to start
##
log "Restarting systemd-journald service"
systemctl restart systemd-journald.service
journalctl --verify

log "Disabling needrestart"
echo "\$nrconf{restart} = 'a';" > /etc/needrestart/conf.d/99-restart.conf
chmod 644 /etc/needrestart/conf.d/99-restart.conf

log "Installation process completed"