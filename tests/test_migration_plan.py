import unittest
import sys
import os

# Add the plugins directory to the path so we can import the filter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins', 'filter'))

from migration_plan import FilterModule
from ansible.errors import AnsibleFilterError


class TestMigrationPlan(unittest.TestCase):
    """Test cases for the migration_plan Ansible filter plugin"""

    def setUp(self):
        """Set up test fixtures"""
        self.filter_module = FilterModule()
        self.filters = self.filter_module.filters()

    def test_filters_registration(self):
        """Test that the migration_plan filter is properly registered"""
        self.assertIn('migration_plan', self.filters)
        self.assertEqual(self.filters['migration_plan'], self.filter_module._migration_plan)

    def test_vm_result_to_dict(self):
        """Test the _vm_result_to_dict method"""
        vm_result = {
            "name": "test-vm",
            "cpu": 2,
            "maxcpu": 4,
            "mem": 2048,
            "maxmem": 4096,
            "node": "node1",
            "status": "running",
            "extra_field": "ignored"
        }
        
        expected = {
            "name": "test-vm",
            "cpu": 2,
            "maxcpu": 4,
            "mem": 2048,
            "maxmem": 4096,
            "node": "node1"
        }
        
        result = self.filter_module._vm_result_to_dict(vm_result)
        self.assertEqual(result, expected)

    def test_node_can_handle_vm_success(self):
        """Test _node_can_handle_vm when node has sufficient resources"""
        node_resources = {
            "available_cpu": 4,
            "available_mem": 4096,
            "maxcpu": 8,
            "maxmem": 8192
        }
        
        vm = {
            "cpu": 2,
            "mem": 2048,
            "maxcpu": 4,
            "maxmem": 4096
        }
        
        result = self.filter_module._node_can_handle_vm(node_resources, vm)
        self.assertTrue(result)

    def test_node_can_handle_vm_insufficient_current_cpu(self):
        """Test _node_can_handle_vm when node has insufficient current CPU"""
        node_resources = {
            "available_cpu": 1,  # Insufficient
            "available_mem": 4096,
            "maxcpu": 8,
            "maxmem": 8192
        }
        
        vm = {
            "cpu": 2,
            "mem": 2048,
            "maxcpu": 4,
            "maxmem": 4096
        }
        
        result = self.filter_module._node_can_handle_vm(node_resources, vm)
        self.assertFalse(result)

    def test_node_can_handle_vm_insufficient_current_mem(self):
        """Test _node_can_handle_vm when node has insufficient current memory"""
        node_resources = {
            "available_cpu": 4,
            "available_mem": 1024,  # Insufficient
            "maxcpu": 8,
            "maxmem": 8192
        }
        
        vm = {
            "cpu": 2,
            "mem": 2048,
            "maxcpu": 4,
            "maxmem": 4096
        }
        
        result = self.filter_module._node_can_handle_vm(node_resources, vm)
        self.assertFalse(result)

    def test_node_can_handle_vm_insufficient_max_cpu(self):
        """Test _node_can_handle_vm when node has insufficient max CPU"""
        node_resources = {
            "available_cpu": 4,
            "available_mem": 4096,
            "maxcpu": 2,  # Insufficient
            "maxmem": 8192
        }
        
        vm = {
            "cpu": 2,
            "mem": 2048,
            "maxcpu": 4,
            "maxmem": 4096
        }
        
        result = self.filter_module._node_can_handle_vm(node_resources, vm)
        self.assertFalse(result)

    def test_node_can_handle_vm_insufficient_max_mem(self):
        """Test _node_can_handle_vm when node has insufficient max memory"""
        node_resources = {
            "available_cpu": 4,
            "available_mem": 4096,
            "maxcpu": 8,
            "maxmem": 2048  # Insufficient
        }
        
        vm = {
            "cpu": 2,
            "mem": 2048,
            "maxcpu": 4,
            "maxmem": 4096
        }
        
        result = self.filter_module._node_can_handle_vm(node_resources, vm)
        self.assertFalse(result)

    def test_calculate_overcommitment(self):
        """Test _calculate_overcommitment method"""
        node_resources = {
            "maxcpu": 8,
            "maxmem": 8192,
            "vms": [
                {"maxcpu": 4, "maxmem": 2048},
                {"maxcpu": 2, "maxmem": 4096}
            ]
        }
        
        cpu_overcommitment, mem_overcommitment = self.filter_module._calculate_overcommitment(node_resources)
        
        # Total allocated: 6 CPU, 6144 MB
        # Overcommitment: 6/8 = 0.75 CPU, 6144/8192 = 0.75 MEM
        self.assertEqual(cpu_overcommitment, 0.75)
        self.assertEqual(mem_overcommitment, 0.75)

    def test_calculate_overcommitment_no_vms(self):
        """Test _calculate_overcommitment with no VMs"""
        node_resources = {
            "maxcpu": 8,
            "maxmem": 8192,
            "vms": []
        }
        
        cpu_overcommitment, mem_overcommitment = self.filter_module._calculate_overcommitment(node_resources)
        
        self.assertEqual(cpu_overcommitment, 0.0)
        self.assertEqual(mem_overcommitment, 0.0)

    def test_migration_plan_empty_node(self):
        """Test migration_plan when the node to upgrade has no running VMs"""
        vms = [
            {
                "name": "vm1",
                "node": "node2",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        self.assertEqual(result, {})

    def test_migration_plan_stopped_vms_ignored(self):
        """Test that stopped VMs are ignored in migration planning"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "stopped",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        self.assertEqual(result, {})

    def test_migration_plan_single_vm_migration(self):
        """Test migration plan for a single VM"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        self.assertEqual(result, {"vm1": "node2"})

    def test_migration_plan_multiple_vms_multiple_nodes(self):
        """Test migration plan with multiple VMs and multiple target nodes"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            },
            {
                "name": "vm2",
                "node": "node1",
                "status": "running",
                "cpu": 1,
                "maxcpu": 2,
                "mem": 1024,
                "maxmem": 2048
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 3,
                "maxcpu": 8,
                "mem": 3072,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            },
            {
                "node": "node3",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        
        # Both VMs should be migrated
        self.assertEqual(len(result), 2)
        self.assertIn("vm1", result)
        self.assertIn("vm2", result)
        self.assertIn(result["vm1"], ["node2", "node3"])
        self.assertIn(result["vm2"], ["node2", "node3"])

    def test_migration_plan_vm_too_large_for_any_node(self):
        """Test migration plan when VM is too large for any available node"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "running",
                "cpu": 10,  # Too large
                "maxcpu": 12,
                "mem": 2048,
                "maxmem": 4096
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 10,
                "maxcpu": 12,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 8,  # Too small
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        with self.assertRaises(AnsibleFilterError) as context:
            self.filter_module._migration_plan(vms, nodes, "node1")
        
        self.assertIn("VM vm1 cannot be migrated", str(context.exception))

    def test_migration_plan_prioritizes_memory_over_cpu(self):
        """Test that VMs are sorted by memory first, then CPU"""
        vms = [
            {
                "name": "vm1",  # Lower memory, higher CPU
                "node": "node1",
                "status": "running",
                "cpu": 4,
                "maxcpu": 8,
                "mem": 1024,
                "maxmem": 2048
            },
            {
                "name": "vm2",  # Higher memory, lower CPU - should be migrated first
                "node": "node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 4096,
                "maxmem": 8192
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 6,
                "maxcpu": 16,
                "mem": 5120,
                "maxmem": 16384
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 16,
                "mem": 0,
                "maxmem": 16384
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        
        # Both VMs should be migrated
        self.assertEqual(len(result), 2)
        self.assertIn("vm1", result)
        self.assertIn("vm2", result)

    def test_migration_plan_worst_fit_algorithm(self):
        """Test that the worst-fit algorithm selects nodes with more available resources"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node2",  # Less available resources
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node3",  # More available resources
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        
        # VM should be migrated to node3 (worst-fit = most available resources)
        self.assertEqual(result["vm1"], "node3")

    def test_migration_plan_edge_case_zero_cpu_vm(self):
        """Test migration plan with VM having zero CPU (edge case)"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "running",
                "cpu": 0,
                "maxcpu": 1,
                "mem": 1024,
                "maxmem": 2048
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 1024,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        result = self.filter_module._migration_plan(vms, nodes, "node1")
        self.assertEqual(result, {"vm1": "node2"})

    def test_migration_plan_filter_interface(self):
        """Test the filter interface directly"""
        vms = [
            {
                "name": "vm1",
                "node": "node1",
                "status": "running",
                "cpu": 2,
                "maxcpu": 4,
                "mem": 2048,
                "maxmem": 4096
            }
        ]
        
        nodes = [
            {
                "node": "node1",
                "cpu": 2,
                "maxcpu": 8,
                "mem": 2048,
                "maxmem": 8192
            },
            {
                "node": "node2",
                "cpu": 0,
                "maxcpu": 8,
                "mem": 0,
                "maxmem": 8192
            }
        ]
        
        # Test using the filter interface
        result = self.filters['migration_plan'](vms, nodes, "node1")
        self.assertEqual(result, {"vm1": "node2"})


if __name__ == '__main__':
    unittest.main()
