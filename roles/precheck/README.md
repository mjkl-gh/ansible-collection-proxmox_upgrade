# Precheck Role

This role performs essential checks before starting a Proxmox upgrade to ensure the system is ready.

## What it does

- Installs the `python3-proxmoxer` package required for Proxmox API communication
- Retrieves all running tasks on the Proxmox node
- Verifies that no tasks are currently running before proceeding with upgrade operations

## Requirements

- Proxmox VE node with API access
- Valid Proxmox API credentials

## Variables

This role uses the following variables that should be defined in your inventory or playbook:

- `proxmox_api_user`: Proxmox API username
- `proxmox_api_password`: Proxmox API password (optional if using tokens)

## Usage

Include this role before running any upgrade operations:

```yaml
- hosts: proxmox_nodes
  roles:
    - adfinis.proxmox_upgrade.precheck
```

The role will fail if any tasks are still running on the node, preventing potential conflicts during the upgrade process.
