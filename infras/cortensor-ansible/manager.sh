#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY_FILE="inventories/hosts.yml"
KEYS_FILE="inventories/group_vars/all/keys.yml"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/cortensor-$(date +%Y%m%d).log"

mkdir -p "${LOG_DIR}"

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

log_message() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$message" >> "$LOG_FILE"
    echo "$message"
}

check_prerequisites() {
    echo "Checking prerequisites..."
    
    if ! command -v ansible-playbook &> /dev/null; then
        print_color $RED "Error: ansible-playbook is not installed or not in PATH"
        echo "Please install Ansible: sudo apt install ansible"
        exit 1
    fi
    
    if [[ ! -f "$INVENTORY_FILE" ]]; then
        print_color $RED "Error: Inventory file '$INVENTORY_FILE' not found"
        echo "Please ensure the inventory.yml file is in the same directory as this script"
        exit 1
    fi
    
    if [[ ! -f "$KEYS_FILE" ]]; then
        print_color $RED "Error: Keys file '$KEYS_FILE' not found"
        echo "Please ensure the keys.yml file is in the same directory as this script"
        exit 1
    fi
    
    print_color $GREEN "Prerequisites check passed ✓"
}

show_hosts() {
    echo "Available hosts:"
    
    if command -v jq &> /dev/null; then
        local inventory_json=$(ansible-inventory -i "$INVENTORY_FILE" --list 2>/dev/null)
        if [[ -n "$inventory_json" ]]; then
            local hosts=$(echo "$inventory_json" | jq -r '._meta.hostvars | keys[]' 2>/dev/null)
            if [[ -n "$hosts" ]]; then
                echo "$hosts" | while read -r host; do
                    local ip=$(echo "$inventory_json" | jq -r "._meta.hostvars[\"$host\"].ansible_host // \"N/A\"" 2>/dev/null)
                    if [[ "$ip" != "N/A" ]]; then
                        echo "  - $host ($ip)"
                    else
                        echo "  - $host"
                    fi
                done
                return
            fi
        fi
    fi
    
    ansible all -i "$INVENTORY_FILE" --list-hosts 2>/dev/null | grep -v "hosts (" | sed 's/^[[:space:]]*/  - /' || {
        echo "Unable to retrieve host list. Please check your inventory file."
    }
}

get_target_hosts() {
    echo ""
    echo "Target Selection:"
    echo "1) All hosts"
    echo "2) Specific host"
    echo "3) Custom group"
    echo ""
    read -p "Select target (1-3): " target_choice
    
    case $target_choice in
        1)
            TARGET_HOSTS="all"
            print_color $GREEN "Selected: All hosts"
            ;;
        2)
            show_hosts
            echo ""
            read -p "Enter hostname: " specific_host
            TARGET_HOSTS="$specific_host"
            print_color $GREEN "Selected: $specific_host"
            ;;
        3)
            read -p "Enter custom host pattern: " custom_hosts
            TARGET_HOSTS="$custom_hosts"
            print_color $GREEN "Selected: $custom_hosts"
            ;;
        *)
            print_color $RED "Invalid selection, using all hosts"
            TARGET_HOSTS="all"
            ;;
    esac
    echo ""
}

run_playbook() {
    local playbook=$1
    local extra_vars=$2
    local description=$3
    
    echo "Starting: $description"
    log_message "Starting $description"
    
    local cmd="ansible-playbook -i $INVENTORY_FILE $playbook"
    
    if [[ -n "$extra_vars" ]]; then
        cmd="$cmd --extra-vars \"$extra_vars\""
    fi
    
    echo "Running: $cmd"
    
    if eval "$cmd"; then
        print_color $GREEN "✓ $description completed successfully"
        log_message "$description completed successfully"
        return 0
    else
        print_color $RED "✗ $description failed"
        log_message "$description failed"
        return 1
    fi
}

deploy_cortensor() {
    echo "=== Cortensor Deployment ==="
    
    get_target_hosts
    
    echo ""
    read -p "Enter Cortensor branch (default: main): " branch
    branch=${branch:-main}
    
    echo ""
    
    local extra_vars="target_hosts=$TARGET_HOSTS cortensor_branch=$branch"
    
    echo ""
    echo "Deployment Configuration:"
    echo "  Targets: $TARGET_HOSTS"
    echo "  Branch: $branch"
    echo ""
    
    read -p "Proceed with deployment? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then\
        run_playbook "playbooks/deploy.yml" "$extra_vars" "Cortensor deployment"
    else
        print_color $RED "Deployment cancelled"
    fi
}

install_monitoring() {
    echo "=== Monitoring Installation ==="
    
    get_target_hosts
    
    local extra_vars="target_hosts=$TARGET_HOSTS"
    
    echo ""
    echo "Monitoring Configuration:"
    echo "  Targets: $TARGET_HOSTS"
    echo ""
    
    read -p "Proceed with monitoring installation? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        run_playbook "playbooks/monitor.yml" "$extra_vars" "Monitoring installation"
    else
        print_color $RED "Monitoring installation cancelled"
    fi
}

update_cortensor() {
    echo "=== Cortensor Update ==="
    
    get_target_hosts
    
    echo ""
    read -p "Enter Cortensor branch (default: main): " branch
    branch=${branch:-main}
    
    local extra_vars="target_hosts=$TARGET_HOSTS cortensor_branch=$branch"
    
    echo ""
    echo "Update Configuration:"
    echo "  Targets: $TARGET_HOSTS"
    echo "  Branch: $branch"
    echo ""
    
    read -p "Proceed with update? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        run_playbook "playbooks/services.yml" "target_hosts=$TARGET_HOSTS service_action=stop" "Stop services"
        run_playbook "playbooks/deploy.yml" "$extra_vars" "Cortensor update"
        run_playbook "playbooks/services.yml" "target_hosts=$TARGET_HOSTS service_action=start" "Start services"
    else
        print_color $RED "Update cancelled"
    fi
}

manage_service() {
    local action=$1
    local description=$2
    
    echo "=== $description ==="
    
    get_target_hosts
    
    local extra_vars="target_hosts=$TARGET_HOSTS service_action=$action"
    
    echo ""
    echo "Service Management:"
    echo "  Targets: $TARGET_HOSTS"
    echo "  Action: $action"
    echo ""
    
    read -p "Proceed with $action? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        run_playbook "playbooks/services.yml" "$extra_vars" "$description"
    else
        print_color $RED "$description cancelled"
    fi
}

register_nodes() {
    echo "=== Node Registration ==="
    
    get_target_hosts
    
    local extra_vars="target_hosts=$TARGET_HOSTS"
    
    echo ""
    echo "Registration Configuration:"
    echo "  Targets: $TARGET_HOSTS"
    echo ""
    
    read -p "Proceed with registration? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        run_playbook "playbooks/register.yml" "$extra_vars" "Node registration"
    else
        print_color $RED "Registration cancelled"
    fi
}

check_status() {
    echo "=== Status Check ==="
    
    get_target_hosts
    
    local extra_vars="target_hosts=$TARGET_HOSTS service_action=status"
    
    run_playbook "playbooks/services.yml" "$extra_vars" "Status check"
}

show_system_info() {
    echo "=== System Information ==="
    echo ""
    echo "Script Directory: $SCRIPT_DIR"
    echo "Inventory File: $INVENTORY_FILE"
    echo "Keys File: $KEYS_FILE"
    echo "Log Directory: $LOG_DIR"
    echo "Current Log: $LOG_FILE"
    echo ""
    echo "Ansible Version:"
    ansible --version | head -n 1
    echo ""
    show_hosts
    echo ""
}

show_menu() {
    clear
    echo "════════════════════════════════════════"
    echo "       Cortensor Management Menu        "
    echo "════════════════════════════════════════"
    echo "  1) Deploy Cortensor nodes             "
    echo "  2) Update Cortensor binary            "
    echo "  3) Install monitoring                 "
    echo "  4) Start services                     "
    echo "  5) Stop services                      "
    echo "  6) Restart services                   "
    echo "  7) Check status                       "
    echo "  8) Register/Verify nodes              "
    echo "  9) System information                 "
    echo "  q) Quit                               "
    echo "════════════════════════════════════════"
    echo ""
}

main() {
    check_prerequisites
    
    while true; do
        show_menu
        read -p "Select an option (1-9, q): " choice
        echo ""
        
        case $choice in
            1)
                deploy_cortensor
                ;;
            2)
                update_cortensor
                ;;
            3)
                install_monitoring
                ;;
            4)
                manage_service "start" "Start services"
                ;;
            5)
                manage_service "stop" "Stop services"
                ;;
            6)
                manage_service "restart" "Restart services"
                ;;
            7)
                check_status
                ;;
            8)
                register_nodes
                ;;
            9)
                show_system_info
                ;;
            q|Q)
                print_color $GREEN "Goodbye!"
                log_message "Script session ended"
                exit 0
                ;;
            *)
                print_color $RED "Invalid option. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

trap 'echo -e "${RED}\nScript interrupted by user${NC}"; exit 130' INT TERM

if [[ $EUID -eq 0 ]]; then
    echo "Warning: Running as root. Consider using a regular user with sudo privileges."
    echo ""
fi

main