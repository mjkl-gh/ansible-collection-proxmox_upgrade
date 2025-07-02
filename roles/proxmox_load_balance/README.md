# Proxmox Load Balance Role

This role automatically balances VM workloads across Proxmox cluster nodes by migrating VMs from overloaded nodes to those with more available resources.

## What it does

- Analyzes the current distribution of VMs across all cluster nodes
- Calculates an optimal load balancing plan based on resource usage
- Migrates VMs between nodes to achieve better resource distribution
- Provides interactive confirmation before executing migrations

## Features

- Smart load balancing algorithm that considers node capacity
- Optional confirmation prompt for migration operations
- Configurable migration timeouts and downtime limits
- Detailed migration plan display before execution

## Variables

### Required Variables
- `proxmox_api_user`: Proxmox API username
- `proxmox_api_password`: Proxmox API password

### Optional Variables
- `proxmox_load_balance_api_hostname`: API hostname (default: `inventory_hostname`)
- `proxmox_load_balance_migration_downtime`: Maximum downtime in seconds (default: 10)
- `proxmox_load_balance_migration_timeout`: Migration timeout in seconds (default: 900)
- `proxmox_load_balance_confirm_migration`: Ask for confirmation before migrating (default: true)

## Usage

```yaml
- hosts: proxmox_cluster
  roles:
    - adfinis.proxmox_upgrade.proxmox_load_balance
```

The role will display the planned migrations and wait for confirmation before proceeding, unless `proxmox_load_balance_confirm_migration` is set to false.
