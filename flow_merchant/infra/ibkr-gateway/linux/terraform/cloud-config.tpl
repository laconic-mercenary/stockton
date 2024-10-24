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
# Disable needrestart
##
log "Disabling needrestart"
echo "\$nrconf{restart} = 'a';" > /etc/needrestart/conf.d/99-restart.conf
chmod 644 /etc/needrestart/conf.d/99-restart.conf

##
# Updates
##
apt-get update -y

##
# Install JAVA
##
log "Installing Java"
apt install -y default-jre
java -version

##
# Check PYTHON
##
log "Checking Python 3"
python3 --version
apt install -y python3-pip

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
cd /usr/local/bin/ibkr_gateway
pip3 install -r requirements.txt


##
# Install necessary utils for clientprotal API
## 
log "Installing necessary utils for clientportal API"
apt install -y unzip
apt install -y jq
wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
chmod a+x /usr/local/bin/yq

jq --version
yq  --version

log "Installing IBKR API"
mkdir -p /opt/ibkr_api
chmod 744 /opt/ibkr_api
echo '${ibkr_api_env_file}' > /opt/ibkr_api/.env

log "Downloading ibkr api"
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh
chmod +x ibgateway-stable-standalone-linux-x64.sh

log "Running - Installing IBKR API"
./ibgateway-stable-standalone-linux-x64.sh

log "Creating log directory"
mkdir -p /opt/ibkr_api/logs
chmod 777 /opt/ibkr_api/logs

chown -R $APPUSER:$APPGROUP /opt/ibkr_api

##
# Turn off SSL
##
log "Disabling SSL for ibkr api"
yq eval '.listenSsl = false' -i /opt/ibkr_api/root/conf.yaml

log "Creating ibkr api service file"
echo '${ibkr_api_service_file}' > /etc/systemd/system/ibkr_api.service
chmod 644 /etc/systemd/system/ibkr_api.service

log "Reloading systemd daemon"
systemctl daemon-reload

log "Enabling ibkr api service"
systemctl enable ibkr_api.service
systemctl start ibkr_api.service

## let the api start so that the gateway can connect to it
sleep 5

log "Enabling gateway service"
systemctl enable ibkr_gateway.service
systemctl start ibkr_gateway.service

##
# digital ocean has a bug that causes systemd-journald to fail to start
##
log "Restarting systemd-journald service"
systemctl restart systemd-journald.service
journalctl --verify

log "Installation process completed"