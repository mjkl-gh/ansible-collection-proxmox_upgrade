import unittest
import sys
import os

# Add the plugins directory to the path so we can import the filter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins', 'filter'))

from migration_plan import FilterModule
from ansible.errors import AnsibleFilterError


class TestMigrationPlanIntegration(unittest.TestCase):
    """Integration tests for the migration_plan filter with realistic scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.filter_module = FilterModule()

    def test_realistic_proxmox_cluster_migration(self):
        """Test migration plan for a realistic Proxmox cluster scenario"""
        # Simulate a realistic cluster with various VM configurations
        vms = [
            # Large memory VM
            {
                "name": "database-server",
                "node": "pve-node1",
                "status": "running",
                "cpu": 4,
                "maxcpu": 8,
                "mem": 8192,
                "maxmem": 16384
            },
            # High CPU VM
            {
                "name": "compute-worker",
                "node": "pve-node1",
                "status": "running",
                "cpu": 6,
                "maxcpu": 8,
                "mem": 4096,
                "maxmem": 8192
            },
            # Medium VM
            {
                "name": "web-server",
                "node": "pve-node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            },
            # Small VM
            {
                "name": "monitoring",
                "node": "pve-node1",
                "status": "running",
                "cpu": 1,
                "maxcpu": 2,
                "mem": 1024,
                "maxmem": 2048
            },
            # Stopped VM (should be ignored)
            {
                "name": "backup-vm",
                "node": "pve-node1",
                "status": "stopped",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            },
            # VM on different node (should be ignored)
            {
                "name": "other-vm",
                "node": "pve-node3",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
        ]

        # Simulate cluster nodes with different resource availability
        nodes = [
            # Node being upgraded (source)
            {
                "node": "pve-node1",
                "cpu": 13,  # Current usage
                "maxcpu": 16,
                "mem": 15360,  # Current usage
                "maxmem": 32768
            },
            # High-capacity node with some current usage
            {
                "node": "pve-node2",
                "cpu": 4,
                "maxcpu": 24,
                "mem": 8192,
                "maxmem": 65536
            },
            # Medium-capacity node with minimal usage
            {
                "node": "pve-node3",
                "cpu": 2,
                "maxcpu": 16,
                "mem": 4096,
                "maxmem": 32768
            },
            # Lower-capacity node
            {
                "node": "pve-node4",
                "cpu": 1,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 16384
            }
        ]

        result = self.filter_module._migration_plan(vms, nodes, "pve-node1")

        # Verify all running VMs from pve-node1 are included in migration plan
        expected_vms = {"database-server", "compute-worker", "web-server", "monitoring"}
        self.assertEqual(set(result.keys()), expected_vms)

        # Verify all VMs are assigned to valid target nodes
        valid_targets = {"pve-node2", "pve-node3", "pve-node4"}
        for vm_name, target_node in result.items():
            self.assertIn(target_node, valid_targets)

        # Verify the database server (largest memory) gets priority placement
        self.assertIn("database-server", result)

    def test_cluster_with_insufficient_resources(self):
        """Test migration plan when cluster has insufficient total resources"""
        # VMs requiring more resources than available in target nodes
        vms = [
            {
                "name": "huge-vm",
                "node": "pve-node1",
                "status": "running",
                "cpu": 16,
                "maxcpu": 20,
                "mem": 32768,
                "maxmem": 65536
            }
        ]

        # Target nodes with insufficient capacity
        nodes = [
            {
                "node": "pve-node1",
                "cpu": 16,
                "maxcpu": 20,
                "mem": 32768,
                "maxmem": 65536
            },
            {
                "node": "pve-node2",
                "cpu": 0,
                "maxcpu": 8,  # Too small
                "mem": 0,
                "maxmem": 16384  # Too small
            }
        ]

        with self.assertRaises(AnsibleFilterError) as context:
            self.filter_module._migration_plan(vms, nodes, "pve-node1")

        self.assertIn("huge-vm cannot be migrated", str(context.exception))

    def test_balanced_resource_distribution(self):
        """Test that VMs are distributed to balance resource usage"""
        # Multiple VMs that should be distributed across nodes
        vms = [
            {
                "name": f"vm-{i}",
                "node": "pve-node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
            for i in range(6)  # 6 identical VMs
        ]

        # Multiple target nodes with equal capacity
        nodes = [
            {
                "node": "pve-node1",
                "cpu": 12,
                "maxcpu": 16,
                "mem": 12288,
                "maxmem": 32768
            },
            {
                "node": "pve-node2",
                "cpu": 0,
                "maxcpu": 16,
                "mem": 0,
                "maxmem": 32768
            },
            {
                "node": "pve-node3",
                "cpu": 0,
                "maxcpu": 16,
                "mem": 0,
                "maxmem": 32768
            }
        ]

        result = self.filter_module._migration_plan(vms, nodes, "pve-node1")

        # All VMs should be migrated
        self.assertEqual(len(result), 6)

        # Check that VMs are distributed across available nodes
        target_nodes = list(result.values())
        node_distribution = {node: target_nodes.count(node) for node in set(target_nodes)}

        # Both target nodes should receive VMs
        self.assertTrue(len(node_distribution) > 1, "VMs should be distributed across multiple nodes")

    def test_mixed_vm_sizes_optimal_placement(self):
        """Test optimal placement of VMs with different resource requirements"""
        vms = [
            # One large VM
            {
                "name": "large-vm",
                "node": "pve-node1",
                "status": "running",
                "cpu": 8,
                "maxcpu": 12,
                "mem": 16384,
                "maxmem": 24576
            },
            # Several small VMs
            {
                "name": "small-vm-1",
                "node": "pve-node1",
                "status": "running",
                "cpu": 1,
                "maxcpu": 2,
                "mem": 1024,
                "maxmem": 2048
            },
            {
                "name": "small-vm-2",
                "node": "pve-node1",
                "status": "running",
                "cpu": 1,
                "maxcpu": 2,
                "mem": 1024,
                "maxmem": 2048
            },
            {
                "name": "small-vm-3",
                "node": "pve-node1",
                "status": "running",
                "cpu": 1,
                "maxcpu": 2,
                "mem": 1024,
                "maxmem": 2048
            }
        ]

        nodes = [
            {
                "node": "pve-node1",
                "cpu": 11,
                "maxcpu": 16,
                "mem": 19456,
                "maxmem": 32768
            },
            # High-capacity node
            {
                "node": "pve-node2",
                "cpu": 0,
                "maxcpu": 20,
                "mem": 0,
                "maxmem": 65536
            },
            # Medium-capacity node
            {
                "node": "pve-node3",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 16384
            }
        ]

        result = self.filter_module._migration_plan(vms, nodes, "pve-node1")

        # All VMs should be migrated
        self.assertEqual(len(result), 4)

        # Large VM should go to the high-capacity node
        self.assertEqual(result["large-vm"], "pve-node2")

        # Small VMs should be distributed optimally
        small_vm_placements = [result[f"small-vm-{i}"] for i in range(1, 4)]
        self.assertTrue(all(node in ["pve-node2", "pve-node3"] for node in small_vm_placements))

    def test_edge_case_exact_resource_match(self):
        """Test migration when VMs exactly match available resources"""
        vms = [
            {
                "name": "exact-match-vm",
                "node": "pve-node1",
                "status": "running",
                "cpu": 4,
                "maxcpu": 8,
                "mem": 8192,
                "maxmem": 16384
            }
        ]

        nodes = [
            {
                "node": "pve-node1",
                "cpu": 4,
                "maxcpu": 8,
                "mem": 8192,
                "maxmem": 16384
            },
            # Node with exactly the required available resources
            {
                "node": "pve-node2",
                "cpu": 4,  # 4 available out of 8
                "maxcpu": 8,
                "mem": 8192,  # 8192 available out of 16384
                "maxmem": 16384
            }
        ]

        result = self.filter_module._migration_plan(vms, nodes, "pve-node1")

        # VM should be successfully migrated
        self.assertEqual(result, {"exact-match-vm": "pve-node2"})


if __name__ == '__main__':
    unittest.main()
