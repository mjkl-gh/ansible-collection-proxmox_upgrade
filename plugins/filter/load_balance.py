#!/usr/bin/env python3
"""
Ansible filter plugin for Proxmox load balancing operations.
"""

from typing import Dict, List, Any

DOCUMENTATION = """
    name: load_balance_plan
    short_description: Create a load balancing plan to distribute VMs evenly across Proxmox nodes
    description:
        - This filter creates a migration plan to distribute VMs evenly across available Proxmox nodes.
        - It analyzes the current VM distribution and creates a plan to balance the load.
        - Only considers online nodes for the load balancing calculation.
    options:
        vms:
            description: List of VM dictionaries containing VM information
            type: list
            elements: dict
            required: true
        nodes:
            description: List of node dictionaries containing node information  
            type: list
            elements: dict
            required: true
    author:
        - Adfinis <support@adfinis.com>
"""

EXAMPLES = """
# Create a load balancing plan for VMs across nodes
- name: Generate load balancing plan
  set_fact:
    migration_plan: "{{ vms | adfinis.proxmox_upgrade.load_balance_plan(nodes) }}"
  vars:
    vms:
      - name: vm1
        node: node1
      - name: vm2
        node: node1
      - name: vm3
        node: node2
    nodes:
      - node: node1
        status: online
      - node: node2
        status: online
      - node: node3
        status: online
"""

RETURN = """
    _value:
        description: Dictionary mapping VM names to migration details
        type: dict
        returned: always
        sample:
            vm1:
                source_node: node1
                target_node: node2
"""


class FilterModule:
    """Ansible filter plugin for load balancing VMs across Proxmox nodes."""

    def filters(self) -> Dict[str, Any]:
        """Return available filters."""
        return {
            "load_balance_plan": self.load_balance_plan,
        }

    def load_balance_plan(
        self, vms: List[Dict], nodes: List[Dict]
    ) -> Dict[str, Dict[str, str]]:
        """
        Create a load balancing plan to distribute VMs evenly across nodes.

        Args:
            vms: List of VM dictionaries with 'name' and 'node' keys
            nodes: List of node dictionaries with 'node' and 'status' keys

        Returns:
            Dictionary mapping VM names to migration details:
            {
                'vm_name': {
                    'source_node': 'current_node',
                    'target_node': 'destination_node'
                }
            }
        """
        if not vms or not nodes:
            return {}

        # Filter only online nodes
        online_nodes = [
            node["node"] for node in nodes if node.get("status") == "online"
        ]

        if len(online_nodes) < 2:
            # No point in load balancing with less than 2 nodes
            return {}

        # Count VMs per node
        vm_count_per_node = {}
        vm_locations = {}

        for node in online_nodes:
            vm_count_per_node[node] = 0

        for vm in vms:
            vm_name = vm.get("name")
            vm_node = vm.get("node")

            if vm_node in online_nodes:
                vm_count_per_node[vm_node] += 1
                vm_locations[vm_name] = vm_node

        # Calculate target distribution
        total_vms = len(vms)
        target_vms_per_node = total_vms // len(online_nodes)
        remainder = total_vms % len(online_nodes)

        # Some nodes will have one extra VM if there's a remainder
        target_distribution = {}
        for i, node in enumerate(sorted(online_nodes)):
            extra = 1 if i < remainder else 0
            target_distribution[node] = target_vms_per_node + extra

        # Create migration plan
        migration_plan = {}

        # Find nodes that have too many VMs
        overloaded_nodes = []
        underloaded_nodes = []

        for node, current_count in vm_count_per_node.items():
            target_count = target_distribution[node]
            if current_count > target_count:
                overloaded_nodes.extend([(node, current_count - target_count)])
            elif current_count < target_count:
                underloaded_nodes.extend([(node, target_count - current_count)])

        # Sort by excess/deficit for optimal distribution
        overloaded_nodes.sort(key=lambda x: x[1], reverse=True)
        underloaded_nodes.sort(key=lambda x: x[1], reverse=True)

        # Create migrations from overloaded to underloaded nodes
        overload_idx = 0
        underload_idx = 0

        while overload_idx < len(overloaded_nodes) and underload_idx < len(
            underloaded_nodes
        ):
            source_node, excess = overloaded_nodes[overload_idx]
            target_node, deficit = underloaded_nodes[underload_idx]

            # Find VMs on the source node that can be migrated
            vms_on_source = [vm for vm in vms if vm.get("node") == source_node]

            migrations_needed = min(excess, deficit)
            migrated = 0

            for vm in vms_on_source:
                if migrated >= migrations_needed:
                    break

                vm_name = vm.get("name")
                if vm_name not in migration_plan:  # Avoid double migration
                    migration_plan[vm_name] = {
                        "source_node": source_node,
                        "target_node": target_node,
                    }
                    migrated += 1

            # Update remaining excess/deficit
            remaining_excess = excess - migrated
            remaining_deficit = deficit - migrated

            if remaining_excess == 0:
                overload_idx += 1
            else:
                overloaded_nodes[overload_idx] = (source_node, remaining_excess)

            if remaining_deficit == 0:
                underload_idx += 1
            else:
                underloaded_nodes[underload_idx] = (target_node, remaining_deficit)

        return migration_plan
