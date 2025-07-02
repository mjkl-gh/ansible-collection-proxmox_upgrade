from ansible.errors import AnsibleFilterError

DOCUMENTATION = """
    name: migration_plan
    short_description: Create a VM migration plan using worst-fit-decreasing algorithm
    description:
        - This filter creates a migration plan to move VMs from a node that needs to be upgraded.
        - Uses a worst-fit-decreasing algorithm to optimally distribute VMs to other nodes.
        - Considers CPU and memory resources, as well as overcommitment ratios.
        - Skips stopped VMs as they don't need migration during upgrades.
    options:
        vms:
            description: List of VM dictionaries containing VM information
            type: list
            elements: dict
            required: true
        nodes:
            description: List of node dictionaries containing node resource information
            type: list
            elements: dict
            required: true
        node_to_upgrade:
            description: Name of the node that needs to be upgraded and VMs migrated from
            type: str
            required: true
    author:
        - Adfinis <support@adfinis.com>
"""

EXAMPLES = """
# Create a migration plan for VMs on a node to be upgraded
- name: Generate migration plan
  set_fact:
    vm_migration_plan: "{{ vms | adfinis.proxmox_upgrade.migration_plan(nodes, 'node1') }}"
  vars:
    vms:
      - name: vm1
        node: node1
        cpu: 2
        maxcpu: 4
        mem: 2048
        maxmem: 4096
        status: running
      - name: vm2
        node: node1
        cpu: 1
        maxcpu: 2
        mem: 1024
        maxmem: 2048
        status: running
    nodes:
      - node: node1
        cpu: 4
        maxcpu: 8
        mem: 4096
        maxmem: 8192
      - node: node2
        cpu: 2
        maxcpu: 8
        mem: 2048
        maxmem: 8192
"""

RETURN = """
    _value:
        description: Dictionary mapping VM names to target node names
        type: dict
        returned: always
        sample:
            vm1: node2
            vm2: node3
"""


class FilterModule(object):
    """Ansible custom filters"""

    def filters(self):
        """Return the custom filters"""
        return {
            "migration_plan": self._migration_plan,
        }

    def _vm_result_to_dict(self, vm_result):
        # create dictionary list with all VMs that contains all the infos we need.
        # We check if the VM has ballooning enabled. If so, we need to check if the current memory is higher than the balloon_min.
        # If it is, we need to use the current memory as the memory requirement otherwise the balloon_min.
        # If ballooning is not enabled, we use the maxmem as the memory requirement.
        return {
            "name": vm_result["name"],
            "cpu": vm_result["cpu"],
            "maxcpu": vm_result["maxcpu"],
            "mem": vm_result["mem"],
            "maxmem": vm_result["maxmem"],
            "node": vm_result["node"],
        }

    def _node_can_handle_vm(self, node_resources, vm):
        """
        Check if a node has enough resources to handle a VM in the current state.
        And ensure that the VMs maxcpu and maxmem are not higher than the nodes maxcpu and maxmem.
        """
        return (
            node_resources["available_cpu"] >= vm["cpu"]
            and node_resources["available_mem"] >= vm["mem"]
            and node_resources["maxcpu"] >= vm["maxcpu"]
            and node_resources["maxmem"] >= vm["maxmem"]
        )

    def _calculate_overcommitment(self, node_resources):
        """
        Calculate the overcommitment score of a node based on CPU and memory requirements of the VMs.
        """
        total_allocated_cpu = sum(vm["maxcpu"] for vm in node_resources["vms"])
        total_allocated_mem = sum(vm["maxmem"] for vm in node_resources["vms"])

        cpu_overcommitment = total_allocated_cpu / node_resources["maxcpu"]
        mem_overcommitment = total_allocated_mem / node_resources["maxmem"]

        return cpu_overcommitment, mem_overcommitment

    def _migration_plan(self, vms, nodes, node_to_upgrade):
        """
        A worst-fit-decreasing algorithm to migrate VMs to other nodes.
        """

        # check if any VMs are running on the node that is to be upgraded
        # if the node is empty, we can skip the migration
        if not any(vm["node"] == node_to_upgrade for vm in vms):
            return {}

        # if the VM isn't running on the node to upgrade, we skip it to avoid unnecessary migrations.
        # we can also skip stopped VMs, as it doesn't matter where they are running.
        proxmox_vms = [
            self._vm_result_to_dict(vm)
            for vm in vms
            if vm["node"] == node_to_upgrade and vm["status"] != "stopped"
        ]

        # create a dictionary with all nodes and it's free resources
        proxmox_nodes = {
            node["node"]: {
                "available_cpu": node["maxcpu"] - node["cpu"],
                "available_mem": node["maxmem"] - node["mem"],
                "maxcpu": node["maxcpu"],
                "maxmem": node["maxmem"],
                "vms": [vm for vm in proxmox_vms if vm["node"] == node["node"]],
            }
            for node in nodes
            if node["node"] != node_to_upgrade
        }

        # sort VMs by RAM and CPU.
        # We prioritize RAM over CPU because CPU causes less issues when overcommitted.
        proxmox_vms.sort(key=lambda vm: (vm["mem"], vm["cpu"]), reverse=True)

        # Dictionary to store which node each VM is assigned to
        migrated_vms = {}

        # Weights for CPU and memory overcommitment
        cpu_weight = 1
        mem_weight = 1

        # Weights for available resources and overcommitment
        available_resources_weight = 1
        overcommitment_weight = 1.25

        # Iterate over each VM and assign it to the node with the worst fit (most available resources)
        for vm in proxmox_vms:
            best_fit_node = None
            best_combined_score = 0

            for node, resources in proxmox_nodes.items():
                # make sure the node has enough resources to accommodate the VMs current requirements.
                # also make sure the VMs maxcpu and maxmem are not higher than the nodes maxcpu and maxmem.
                if self._node_can_handle_vm(resources, vm):
                    # Calculate overcommitment for the node, considering its current VMs
                    cpu_overcommitment, mem_overcommitment = (
                        self._calculate_overcommitment(resources)
                    )
                    overcommitment_score = (cpu_overcommitment * cpu_weight) + (
                        mem_overcommitment * mem_weight
                    )

                    available_cpu = resources["available_cpu"] / max(vm["cpu"], 0.0001)
                    available_mem = resources["available_mem"] / max(vm["mem"], 1)
                    available_resource_score = (available_cpu * cpu_weight) + (
                        available_mem * mem_weight
                    )

                    # Combine the two scores (higher combined score is better)
                    combined_score = (
                        available_resource_score * available_resources_weight
                    ) - (overcommitment_score * overcommitment_weight)

                    if combined_score > best_combined_score:
                        best_fit_node = node
                        best_combined_score = combined_score

            # If a node is found, allocate the VM to that node
            if best_fit_node:
                migrated_vms[vm["name"]] = best_fit_node

                # Update the node's available resources
                proxmox_nodes[best_fit_node]["available_cpu"] -= vm["cpu"]
                proxmox_nodes[best_fit_node]["available_mem"] -= vm["mem"]
            else:
                raise AnsibleFilterError(
                    f"VM {vm['name']} cannot be migrated. Reasons: "
                    f"CPU: needed {vm['cpu']}, "
                    f"Mem: needed {vm['mem']})"
                )

        return migrated_vms
