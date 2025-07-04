#!/bin/bash
export DEBIAN_FRONTEND="noninteractive"
WORKDIR=$HOME/cortensor-docker
sudo apt-get update -qy > /dev/null 2>&1
sudo apt-get install -y -qq curl ca-certificates sudo > /dev/null 2>&1
source <(curl -s https://raw.githubusercontent.com/CryptoNodeID/helper-script/master/common.sh)
base_colors
header_info
color
catch_errors

PUB_KEY=""
PRIV_KEY=""
RPC_URL=""
ETH_RPC_URL=""
CONTRACT_ADDRESS_RUNTIME=""
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""
COUNT=0
START_PORT=49001

# Check if the shell is using bash
shell_check

docker_check(){
# Check and install docker if not available
if ! command -v docker &> /dev/null; then
  msg_info "Installing docker..."
  for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove -qy $pkg > /dev/null 2>&1; done
  sudo apt-get update -qy > /dev/null 2>&1
  sudo apt-get -qy install curl > /dev/null 2>&1
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null 2>&1
  sudo apt-get update -qy > /dev/null 2>&1
  sudo apt-get install -qy docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER
fi
msg_ok "Docker has been installed."
}
install_cortensor() {
docker_check

cd $WORKDIR

tee Dockerfile > /dev/null << EOF
FROM ipfs/kubo:v0.33.2 AS ipfs

FROM ubuntu:24.04

# Install necessary packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    apt-transport-https \
    ca-certificates 

COPY --from=ipfs /usr/local/bin/ipfs /usr/local/bin/ipfs

# Clone the Cortensor installer repository
RUN git clone https://github.com/cortensor/installer.git /opt/cortensor-installer

WORKDIR /opt/cortensor-installer

RUN mkdir /home/deploy && cp -r dist /home/deploy/.cortensor

WORKDIR /home/deploy/.cortensor

COPY run.sh /home/deploy/.cortensor/run.sh

RUN chmod +x cortensord \
  && mkdir logs \
  && mkdir llm-files \
  && cp .env-example .env \
  && cp cortensor.service /etc/systemd/system \
  && touch logs/cortensord.log \
  && touch logs/cortensord-llm.log \
  && chmod +x run.sh

USER root
CMD ["/bin/bash", "-c", "/home/deploy/.cortensor/run.sh"]

EOF
tee run.sh > /dev/null << EOF
#!/bin/bash

if [ -n "\$RPC_URL" ]; then
  sed -i "s|^HOST=.*|HOST=\${RPC_URL//&/\\&}|" .env
fi

if [ -n "\$ETH_RPC_URL" ]; then
  sed -i "s|^HOST_MAINNET=.*|HOST_MAINNET=\${ETH_RPC_URL//&/\\&}|" .env
else
  ETH_RPC_URL=https://ethereum-rpc.publicnode.com
  sed -i "s|^HOST_MAINNET=.*|HOST_MAINNET=\${ETH_RPC_URL//&/\\&}|" .env
fi

if [ -n "\$PUBLIC_KEY" ]; then
  sed -i "s/^NODE_PUBLIC_KEY=.*/NODE_PUBLIC_KEY=\$PUBLIC_KEY/" .env
fi

if [ -n "\$PRIVATE_KEY" ]; then
  sed -i "s/^NODE_PRIVATE_KEY=.*/NODE_PRIVATE_KEY=\$PRIVATE_KEY/" .env
fi

if [ -n "\$LLM_HOST" ]; then
  sed -i "s/^LLM_HOST=.*/LLM_HOST=\$LLM_HOST/" .env
fi

if [ -n "\$LLM_PORT" ]; then
  sed -i "s/^LLM_PORT=.*/LLM_PORT=\$LLM_PORT/" .env
fi

if [ -n "\$CONTRACT_ADDRESS_RUNTIME" ]; then
  sed -i "s/^CONTRACT_ADDRESS_RUNTIME=.*/CONTRACT_ADDRESS_RUNTIME=\$CONTRACT_ADDRESS_RUNTIME/" .env
fi


/home/deploy/.cortensor/cortensord .env tool register
/home/deploy/.cortensor/cortensord .env tool verify
/home/deploy/.cortensor/cortensord .env minerv4 1 docker
EOF
msg_info "Building Cortensor..."
sudo docker build -t cortensor-image:latest -f Dockerfile . >/dev/null 2>&1
msg_ok "Cortensor has been built."
rm -rf Dockerfile run.sh
msg_ok "Cortensor has been installed."

if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor" --yesno "Do you want to run the Cortensor?" 10 60); then
    msg_info "Starting Cortensor... (first run may take a while *please take some coffee*)"
    sudo docker compose -f $WORKDIR/docker-compose.yml up -d >/dev/null 2>&1
    msg_ok "Cortensor started successfully.\n"
fi
echo -e "${INFO}${GN} To start Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml up -d'${CL}"
echo -e "${INFO}${GN} To stop Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml down'${CL}"
echo -e "${INFO}${GN} To restart Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml restart'${CL}"
echo -e "${INFO}${GN} To check the logs of Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml logs -fn 100'${CL}"
}

update_cortensor() {
if [ -d "$WORKDIR" ]; then
    cd $WORKDIR
    msg_info "Stopping Cortensor..."
    sudo docker compose -f $WORKDIR/docker-compose.yml down >/dev/null 2>&1
    sudo docker compose -f $WORKDIR/docker-compose.yml rm >/dev/null 2>&1
    msg_ok "Cortensor has been stopped."
    msg_info "Removing existing Cortensor..."
    sudo docker rmi -f cortensor-image:latest >/dev/null 2>&1
    sudo docker rmi -f $(sudo docker images -f "dangling=true" -q) >/dev/null 2>&1
    sudo docker system prune -f >/dev/null 2>&1
    msg_ok "Old Cortensor has been removed."
    tee Dockerfile > /dev/null << EOF
FROM ipfs/kubo:v0.33.2 AS ipfs

FROM ubuntu:24.04

# Install necessary packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    apt-transport-https \
    ca-certificates 

COPY --from=ipfs /usr/local/bin/ipfs /usr/local/bin/ipfs

# Clone the Cortensor installer repository
RUN git clone https://github.com/cortensor/installer.git /opt/cortensor-installer

WORKDIR /opt/cortensor-installer

RUN mkdir /home/deploy && cp -r dist /home/deploy/.cortensor

WORKDIR /home/deploy/.cortensor

COPY run.sh /home/deploy/.cortensor/run.sh

RUN chmod +x cortensord \
  && mkdir logs \
  && mkdir llm-files \
  && cp .env-example .env \
  && cp cortensor.service /etc/systemd/system \
  && touch logs/cortensord.log \
  && touch logs/cortensord-llm.log \
  && chmod +x run.sh

USER root
CMD ["/bin/bash", "-c", "/home/deploy/.cortensor/run.sh"]

EOF
tee run.sh > /dev/null << EOF
#!/bin/bash

if [ -n "\$RPC_URL" ]; then
  sed -i "s|^HOST=.*|HOST=\${RPC_URL//&/\\&}|" .env
fi

if [ -n "\$ETH_RPC_URL" ]; then
  sed -i "s|^HOST_MAINNET=.*|HOST_MAINNET=\${ETH_RPC_URL//&/\\&}|" .env
else
  ETH_RPC_URL=https://ethereum-rpc.publicnode.com
  sed -i "s|^HOST_MAINNET=.*|HOST_MAINNET=\${ETH_RPC_URL//&/\\&}|" .env
fi

if [ -n "\$PUBLIC_KEY" ]; then
  sed -i "s/^NODE_PUBLIC_KEY=.*/NODE_PUBLIC_KEY=\$PUBLIC_KEY/" .env
fi

if [ -n "\$PRIVATE_KEY" ]; then
  sed -i "s/^NODE_PRIVATE_KEY=.*/NODE_PRIVATE_KEY=\$PRIVATE_KEY/" .env
fi

if [ -n "\$LLM_HOST" ]; then
  sed -i "s/^LLM_HOST=.*/LLM_HOST=\$LLM_HOST/" .env
fi

if [ -n "\$LLM_PORT" ]; then
  sed -i "s/^LLM_PORT=.*/LLM_PORT=\$LLM_PORT/" .env
fi

if [ -n "\$CONTRACT_ADDRESS_RUNTIME" ]; then
  sed -i "s/^CONTRACT_ADDRESS_RUNTIME=.*/CONTRACT_ADDRESS_RUNTIME=\$CONTRACT_ADDRESS_RUNTIME/" .env
fi

/home/deploy/.cortensor/cortensord .env minerv4 1 docker
EOF
    msg_info "Building Cortensor..."
    sudo docker build --no-cache -t cortensor-image:latest -f Dockerfile . >/dev/null 2>&1
    msg_ok "Cortensor has been built."
    rm -rf Dockerfile run.sh
    msg_ok "Cortensor has been updated."
else
    msg_error "Cortensor is not installed. Please run the installation script first."
fi
    if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor" --yesno "Do you want to run the updated Cortensor?" 10 60); then
        msg_info "Starting Cortensor... (first run may take a while *please take some coffee*)"
        sudo docker compose -f $WORKDIR/docker-compose.yml up -d >/dev/null 2>&1
        msg_ok "Cortensor started successfully.\n"
    fi
    echo -e "${INFO}${GN} To start Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml up -d'${CL}"
    echo -e "${INFO}${GN} To stop Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml down'${CL}"
    echo -e "${INFO}${GN} To restart Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml restart'${CL}"
    echo -e "${INFO}${GN} To check the logs of Cortensor, run the command: 'sudo docker compose -f $WORKDIR/docker-compose.yml logs -fn 100'${CL}"
}

init_cortensor() {
if [ -d "$WORKDIR" ]; then
    if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --yesno "Cortensor folder already exists. This will reinstall the Cortensor Node. Do you want to continue?" 10 60); then
        msg_info "Removing existing Cortensor folder..."
        sudo rm -rf $WORKDIR
        msg_ok "Cortensor folder has been removed."
    else
        exit_script
    fi
fi
mkdir -p $WORKDIR
echo "# Environment variables for cortensor nodes" > $WORKDIR/.env
echo "# Please fill in the values for NODE_PUBLIC_KEY, NODE_PRIVATE_KEY, RPC_URL, ETH_RPC_URL, CONTRACT_ADDRESS_RUNTIME" >> $WORKDIR/.env
if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --yesno "This script will install the Cortensor Node. Do you want to continue?" 10 60); then
    while [ -z "$RPC_URL" ]; do
      if RPC_URL=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --inputbox "Input your RPC URL (Default: https://arb-sepolia.cryptonode.id):" 8 60 "https://arb-sepolia.cryptonode.id" 3>&1 1>&2 2>&3); then
        if [[ $RPC_URL != http* ]]; then
            whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --msgbox "Error: RPC URL must start with http" 8 60
            RPC_URL=""
        elif (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --yesno "\nRPC URL: $RPC_URL\n\nContinue with the installation?" 10 60); then
            echo "RPC_URL=$RPC_URL" >> $WORKDIR/.env
            break
        else
            RPC_URL=""
        fi
      else
        exit_script
      fi
    done
    while [ -z "$ETH_RPC_URL" ]; do
      if ETH_RPC_URL=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --inputbox "Input your Ethereum RPC URL (Default: https://ethereum-rpc.publicnode.com):" 8 60 "https://ethereum-rpc.publicnode.com" 3>&1 1>&2 2>&3); then
        if [[ $ETH_RPC_URL != http* ]]; then
            whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --msgbox "Error: Ethereum RPC URL must start with http" 8 60
            ETH_RPC_URL=""
        elif (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --yesno "\nEthereum RPC URL: $ETH_RPC_URL\n\nContinue with the installation?" 10 60); then
            echo "ETH_RPC_URL=$ETH_RPC_URL" >> $WORKDIR/.env
            break
        else
            ETH_RPC_URL=""
        fi
      else
        exit_script
      fi
    done
    while [ -z "$CONTRACT_ADDRESS_RUNTIME" ]; do
      if CONTRACT_ADDRESS_RUNTIME=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --inputbox "Input your contract address runtime (Default: 0x8361E7821bDAD7F8F0aC7862Bebb190B8Da1A160):" 8 60 "0x8361E7821bDAD7F8F0aC7862Bebb190B8Da1A160" 3>&1 1>&2 2>&3); then
        if [[ $CONTRACT_ADDRESS_RUNTIME != 0x* ]]; then
            whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --msgbox "Error: Contract Address Runtime must start with 0x" 8 60
            CONTRACT_ADDRESS_RUNTIME=""
        elif (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --yesno "\nContract Address Runtime: $CONTRACT_ADDRESS_RUNTIME\n\nContinue with the installation?" 10 60); then
            echo "CONTRACT_ADDRESS_RUNTIME=$CONTRACT_ADDRESS_RUNTIME" >> $WORKDIR/.env
            break
        else
            CONTRACT_ADDRESS_RUNTIME=""
        fi
      else
        exit_script
      fi
    done
    echo "# Node public and private keys" >> $WORKDIR/.env
    COUNT=0
    if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" --yesno "Do you want to add your node address?\nYes: you will need to input your address and privatekey\nNo: You will be prompted on how many addresses you want to add later" 10 65); then
      while true; do
        while true; do
          PUB_KEY=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
            --inputbox "Input your public key (EVM starting with 0x):" 8 60 3>&1 1>&2 2>&3)
          [ $? -ne 0 ] && exit_script
          if [[ $PUB_KEY == 0x* ]]; then
            break
          else
            whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
              --msgbox "Error: Public Key must start with 0x" 8 60
          fi
        done
        while true; do
          PRIV_KEY=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
            --inputbox "Input your private key (EVM starting with 0x):" 8 60 3>&1 1>&2 2>&3)
          [ $? -ne 0 ] && exit_script
          if [[ $PRIV_KEY == 0x* ]]; then
            break
          else
            whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
              --msgbox "Error: Private Key must start with 0x" 8 60
          fi
        done
        COUNT=$((COUNT + 1))
        echo "NODE_PUBLIC_KEY_$COUNT=$PUB_KEY" >> "$WORKDIR/.env"
        echo "NODE_PRIVATE_KEY_$COUNT=$PRIV_KEY" >> "$WORKDIR/.env"
        if ! whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
          --yesno "\nPublic Key: $PUB_KEY\nPrivate Key: $PRIV_KEY\n\nAdd another node address?" 12 60; then
          break
        fi
      done
    whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
      --msgbox "\n$COUNT address(es) added successfully.\nContinuing with installation..." 10 60
    else
      while true; do
        COUNT=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
          --inputbox "Input the number of nodes you want to add (Default: 1):" 8 60 "1" 3>&1 1>&2 2>&3)
        [ $? -ne 0 ] && exit_script
        if [[ $COUNT =~ ^[0-9]+$ ]] && [ "$COUNT" -gt 0 ]; then
          for ((i=1; i<=$COUNT; i++)); do
              echo "NODE_PUBLIC_KEY_$i=" >> "$WORKDIR/.env"
              echo "NODE_PRIVATE_KEY_$i=" >> "$WORKDIR/.env"
          done
          break
        else
          whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
            --msgbox "Error: Please enter a valid number greater than 0." 8 60
        fi
      done
      whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
      --msgbox "\n$COUNT address(es) skeleton added successfully.\nContinuing with installation..." 10 60
    fi
    
    cat > $WORKDIR/docker-compose.yml <<EOF
services:
EOF
    for ((i=1; i<=$COUNT; i++)); do
      port=$((START_PORT + i - 1))
    cat >> $WORKDIR/docker-compose.yml <<EOF
  cortensor-$i:
    image: cortensor-image
    container_name: cortensor-$i
    restart: unless-stopped
    environment:
      RPC_URL: "\${RPC_URL}"
      ETH_RPC_URL: "\${ETH_RPC_URL}"
      PUBLIC_KEY: "\${NODE_PUBLIC_KEY_$i}"
      PRIVATE_KEY: "\${NODE_PRIVATE_KEY_$i}"
      CONTRACT_ADDRESS_RUNTIME: "\${CONTRACT_ADDRESS_RUNTIME}"
      LLM_HOST: "llm-$i"
      LLM_PORT: "$port"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    extra_hosts:
      - "host.docker.internal:host-gateway"

  llm-$i:
    image: cortensor/llm-engine-default-0
    container_name: cts-llm-$i
    restart: always
    working_dir: /app
    environment:
      PYTHONUNBUFFERED: "True"
      APP_HOME: /app
      PORT: "$port"
      HOST: "0.0.0.0"
      CPU_THREADS: "4"
    command: ["/app/llava-v1.5-7b-q4.llamafile --host \$\$HOST --port \$\$PORT --nobrowser --mlock -t \$\$CPU_THREADS"]
    extra_hosts:
      - "host.docker.internal:host-gateway"

EOF
    done
    msg_ok "Cortensor config has been initialized."
    install_cortensor
else
    exit_script
fi
}
install_monitoring() {
if [ -d "$WORKDIR" ]; then
MONITORING_DIR="$HOME/cortensor-watcher-bot"
RPC_URL=$(grep "^RPC_URL=" $WORKDIR/.env | cut -d'=' -f2)
if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Monitoring" --yesno "This script will install the Cortensor Monitoring. Do you want to continue?" 10 60); then
  while true; do
    while [ -z "$TELEGRAM_BOT_TOKEN" ]; do
      if TELEGRAM_BOT_TOKEN=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Monitoring" --inputbox "Input your Telegram Bot Token (get from @BotFather):" 8 60 3>&1 1>&2 2>&3); then
          continue
      else
        exit_script
      fi
    done
    while [ -z "$TELEGRAM_CHAT_ID" ]; do
      if TELEGRAM_CHAT_ID=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Monitoring" --inputbox "Input your Telegram Chat ID (Default: 123456789):" 8 60 "123456789" 3>&1 1>&2 2>&3); then
        if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Monitoring" --yesno "\nTelegram Bot Token: $TELEGRAM_BOT_TOKEN\nTelegram Chat ID: $TELEGRAM_CHAT_ID\n\nContinue with the installation?" 10 60); then
            continue
        else
            TELEGRAM_BOT_TOKEN=""
            TELEGRAM_CHAT_ID=""
        fi
      else
        exit_script
      fi
    done
    break
  done
else
    exit_script
fi

if [ -d "$MONITORING_DIR" ]; then
  msg_info "Removing existing Cortensor Monitoring folder..."
  sudo rm -rf $MONITORING_DIR
  msg_ok "Cortensor Monitoring folder has been removed."
fi

msg_info "Installing Cortensor Monitoring..."
git clone --filter=blob:none --no-checkout https://github.com/cortensor/community-projects.git && \
cd community-projects && \
git sparse-checkout init --cone && \
git sparse-checkout set tools/cortensor-watcher-bot && \
git checkout main && \
mv tools/cortensor-watcher-bot ../cortensor-watcher-bot && \
cd .. && \
rm -rf community-projects

msg_ok "Cortensor Monitoring has been initialized."

echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" > $MONITORING_DIR/.env
echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID" >> $MONITORING_DIR/.env
echo "RPC_URL=$RPC_URL" >> $MONITORING_DIR/.env

json="{\"containers\": ["
while IFS= read -r line; do
  if [[ $line == NODE_PUBLIC_KEY_* ]]; then
    number=$(echo "$line" | cut -d'=' -f1 | grep -o '[0-9]\+')
    pub_key=$(echo "$line" | cut -d'=' -f2)
    json+="\"cortensor-$number\", "
  fi
done < $HOME/cortensor-docker/.env
json="${json%, }], \"node_addresses\": {"
while IFS= read -r line; do
  if [[ $line == NODE_PUBLIC_KEY_* ]]; then
    number=$(echo "$line" | cut -d'=' -f1 | grep -o '[0-9]\+')
    pub_key=$(echo "$line" | cut -d'=' -f2)
    json+="\"cortensor-$number\": \"$pub_key\", "
  fi
done < $HOME/cortensor-docker/.env
json="${json%, }}, \"watch_tx_for_containers\": ["
while IFS= read -r line; do
  if [[ $line == NODE_PUBLIC_KEY_* ]]; then
    number=$(echo "$line" | cut -d'=' -f1 | grep -o '[0-9]\+')
    pub_key=$(echo "$line" | cut -d'=' -f2)
    json+="\"cortensor-$number\", "
  fi
done < $HOME/cortensor-docker/.env
json="${json%, }], \"tail_lines\": 500, \"check_interval_seconds\": 900, \"grace_period_seconds\": 930, \"stats_api_url\": \"https://lb-be-5.cortensor.network/network-stats-tasks\", \"tx_timeout_seconds\": 45, \"stagnation_alert_enabled\": true, \"stagnation_threshold_minutes\": 30, \"reputation_check_enabled\": true, \"reputation_api_base_url\": \"https://lb-be-5.cortensor.network/reputation/\", \"reputation_check_window\": 20, \"reputation_failure_threshold\": 5, \"reputation_restart_cooldown_minutes\": 30}"
echo "$json" | jq . | tee $MONITORING_DIR/config.json
msg_ok "Cortensor Monitoring configuration file created successfully."

if (whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Monitoring" --yesno "Do you want to start the Cortensor Monitoring now?" 10 60); then
  msg_info "Starting Cortensor Monitoring... (first run may take a while *please take some coffee*)"
  docker compose -f $MONITORING_DIR/docker-compose.yml up -d
  msg_ok "Cortensor Monitoring started successfully."
  echo "Monitoring installed successfully."
  exit_script
fi

else
    whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor Node" \
      --msgbox "\nPlease install Cortensor Node first." 10 60
    init_cortensor
fi
}

while true; do
    choice=$(whiptail --backtitle "CryptoNodeID Helper Scripts" --title "Cortensor-Node" --menu "Choose the type of Cortensor-Node to install:" 10 70 4 \
        "Install" "     Install the Cortensor Node (Default)" \
        "Update" "     Update the Cortensor Node" \
        "Install Monitoring" "     Install Monitoring for Cortensor Node" \
        "Exit" "     Exit the script"  --nocancel --default-item "Install" 3>&1 1>&2 2>&3)

    if [ $? -ne 0 ]; then
      echo -e "${CROSS}${RD} Menu canceled. Exiting.${CL}"
      exit 0
    fi

    case $choice in
        "Install")
          init_cortensor
          break
          ;;
        "Update")
          update_cortensor
          break
          ;;
        "Install Monitoring")
          install_monitoring
          break
          ;;
        "Exit")
          exit_script
          ;;
        *)
          echo -e "${CROSS}${RD}Invalid option, please try again.${CL}"
          ;;
    esac
done
