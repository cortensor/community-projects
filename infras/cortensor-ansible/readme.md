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
   - `inventory.yml`: Define your target hosts and group variables.
   - `keys.yml`: Manage your SSH keys and credentials.

2. Ensure you have the necessary permissions and access to manage the target nodes.

## Usage

1. **Deploy to All Nodes**:
   ```bash
   ansible-playbook -i inventory.yml cortensor-deploy.yml
   ```

2. **Deploy to a Specific Node**:
   ```bash
   ansible-playbook -i inventory.yml cortensor-deploy.yml --limit node1
   ```

3. **Manage Services**:
   ```bash
   ansible-playbook cortensor-service.yml -e "service_action=started"
   ansible-playbook cortensor-service.yml -e "service_action=stopped"
   ansible-playbook cortensor-service.yml -e "service_action=restarted"
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
