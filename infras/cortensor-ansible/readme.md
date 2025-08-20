# Cortensor Ansible (Restructured)

## Layout
```
cortensor-ansible/
├── ansible.cfg
├── inventories/
│   ├── group_vars/
│   │   └── all/
│   │       ├── main.yml
│   │       └── keys.yml
│   └── hosts.yml
├── roles/
│   ├── cortensor/
│   │   ├── handlers/
│   │   │   └── main.yml
│   │   ├── tasks/
│   │   │   ├── install.yml
│   │   │   ├── deploy.yml
│   │   │   ├── register.yml
│   │   │   └── main.yml
│   │   └── templates/
│   │       └── cortensor-instance.service.j2
│   └── alloy/
│       ├── handlers/
│       │   └── main.yml
│       ├── tasks/
│       │   ├── install.yml
│       │   └── main.yml
│       └── templates/
│           └── config.alloy.j2
├── playbooks/
│   ├── deploy.yml
│   ├── register.yml
│   └── services.yml
├── README.md
├── RELEASE.md
├── LICENSE
└── manager.sh
```

# Cortensor Deployment

This repository contains scripts and playbooks for deploying Cortensor infrastructure using Ansible. Follow the instructions below to set up and manage your Cortensor nodes.

## Prerequisites

1. **Install Ansible**: Ensure Ansible is installed on your control machine. You can install it using the following command:
   ```bash
   sudo apt update
   sudo apt install software-properties-common
   sudo add-apt-repository --yes --update ppa:ansible/ansible
   sudo apt install ansible-core
   ```

## Setup

1. Review and update the inventory and configuration files as needed:
   - `inventories/hosts.yml`: Define your servers, keys amd other parameter related to cortensor nodes.
   - `inventories/group_vars/all/main.yml`: Define username and keys for SSH, rpc and other variables.
   - `inventories/group_vars/all/keys.yml`: Wallet Private and Public Keys.

2. Ensure you have the necessary permissions and access to manage the target nodes.

## Usage

1. **Deploy to All Nodes**:
   ```bash
   ansible-playbook -i inventories/hosts.yml playbooks/deploy.yml
   ```

2. **Deploy to a Specific Node**:
   ```bash
   ansible-playbook -i inventories/hosts.yml playbooks/deploy.yml --limit node1
   ```

3. **Manage Services**:
   ```bash
   ansible-playbook playbooks/services.yml -e "service_action=start"
   ansible-playbook playbooks/services.yml -e "service_action=stop"
   ansible-playbook playbooks/services.yml -e "service_action=restart"
   ```

OR **Use Manager Script**: To perform deployment tasks, use the `manager.sh` script:
   ```bash
   ./manager.sh
   ```

## Notes

- Ensure that all nodes are accessible via SSH and have the necessary Ansible Python dependencies installed.
- Review the playbooks and scripts for any environment-specific changes you may need.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
