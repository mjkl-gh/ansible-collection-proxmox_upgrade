# Proxmox Upgrade Role

This role performs safe, rolling upgrades of Proxmox VE nodes in a cluster by automatically migrating VMs and handling the upgrade process.

## What it does

- Ensures only one node is upgraded at a time to maintain cluster stability
- Creates an intelligent migration plan to move VMs away from the node being upgraded
- Migrates all VMs to other available cluster nodes
- Performs system package upgrades using apt
- Reboots the node and waits for it to come back online
- Verifies the node is healthy and ready for normal operations

## Key Features

- Safe rolling upgrade process that maintains VM availability
- Automatic VM migration with customizable downtime limits
- Interactive confirmation before VM migrations
- Comprehensive error handling and validation
- Post-upgrade health verification

## Variables

### Required Variables
- `proxmox_api_user`: Proxmox API username
- `proxmox_api_password`: Proxmox API password

### Optional Variables
- `proxmox_upgrade_api_hostname`: API hostname (default: `inventory_hostname`)
- `proxmox_upgrade_mode`: apt upgrade mode (default: `dist`)
- `proxmox_upgrade_autoremove`: Remove unused packages after upgrade (default: true)
- `proxmox_upgrade_migration_downtime`: Max VM downtime in seconds (default: 10)
- `proxmox_upgrade_migration_timeout`: Migration timeout in seconds (default: 600)
- `proxmox_upgrade_reboot_timeout`: Reboot timeout in seconds (default: 600)
- `proxmox_upgrade_confirm_migration`: Ask for confirmation before migrating (default: true)

## Usage

```yaml
- hosts: proxmox_nodes
  serial: 1  # Important: upgrade one node at a time
  roles:
    - adfinis.proxmox_upgrade.proxmox_upgrade
```

The role enforces that only one node is processed at a time and will display the migration plan before proceeding with VM migrations.
