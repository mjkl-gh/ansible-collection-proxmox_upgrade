#!/usr/bin/env python3
"""
Test script for the proxmox_load_balance role filter.
"""

import sys
import os

# Add the filter path relative to the tests directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins', 'filter'))

try:
    from load_balance import FilterModule
except ImportError:
    print("Error: Unable to import load_balance module")
    sys.exit(1)

def test_load_balance_plan():
    """Test the load_balance_plan filter."""
    filter_module = FilterModule()
    
    # Test data with more realistic VM resource information
    vms = [
        {
            'name': 'vm1', 'node': 'node1', 'status': 'running',
            'cpu': 2, 'mem': 4096, 'maxcpu': 4, 'maxmem': 8192
        },
        {
            'name': 'vm2', 'node': 'node1', 'status': 'running',
            'cpu': 4, 'mem': 8192, 'maxcpu': 8, 'maxmem': 16384
        },
        {
            'name': 'vm3', 'node': 'node1', 'status': 'running',
            'cpu': 1, 'mem': 2048, 'maxcpu': 2, 'maxmem': 4096
        },
        {
            'name': 'vm4', 'node': 'node2', 'status': 'running',
            'cpu': 1, 'mem': 1024, 'maxcpu': 2, 'maxmem': 2048
        },
        {
            'name': 'vm5', 'node': 'node3', 'status': 'stopped',
            'cpu': 2, 'mem': 4096, 'maxcpu': 4, 'maxmem': 8192
        },
    ]
    
    nodes = [
        {'node': 'node1', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768},
        {'node': 'node2', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768},
        {'node': 'node3', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768},
    ]
    
    # Execute the filter
    result = filter_module.load_balance_plan(vms, nodes)
    
    print("Test VMs distribution (running VMs only):")
    vm_count_per_node = {}
    for vm in vms:
        if vm['status'] == 'running':
            node = vm['node']
            vm_count_per_node[node] = vm_count_per_node.get(node, 0) + 1
    
    for node, count in vm_count_per_node.items():
        print(f"  {node}: {count} VMs")
    
    print(f"\nLoad balancing plan: {result}")
    
    # Verify the result
    if isinstance(result, dict):
        print("✓ Load balance plan generated successfully")
        if len(result) > 0:
            print(f"✓ {len(result)} VMs planned for migration")
            for vm_name, migration in result.items():
                print(f"  {vm_name}: {migration['source_node']} → {migration['target_node']}")
        else:
            print("✓ No migrations needed - cluster is already balanced")
    else:
        print("✗ Load balance plan should return a dictionary")
        return False
    
    return True

def test_edge_cases():
    """Test edge cases."""
    filter_module = FilterModule()
    
    # Test with empty VMs
    result = filter_module.load_balance_plan([], [{'node': 'node1', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768}])
    assert result == {}, "Empty VMs should return empty plan"
    
    # Test with empty nodes
    result = filter_module.load_balance_plan([{
        'name': 'vm1', 'node': 'node1', 'status': 'running',
        'cpu': 2, 'mem': 4096, 'maxcpu': 4, 'maxmem': 8192
    }], [])
    assert result == {}, "Empty nodes should return empty plan"
    
    # Test with single node
    result = filter_module.load_balance_plan(
        [{
            'name': 'vm1', 'node': 'node1', 'status': 'running',
            'cpu': 2, 'mem': 4096, 'maxcpu': 4, 'maxmem': 8192
        }], 
        [{'node': 'node1', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768}]
    )
    assert result == {}, "Single node should not need rebalancing"
    
    # Test with only stopped VMs
    result = filter_module.load_balance_plan(
        [{
            'name': 'vm1', 'node': 'node1', 'status': 'stopped',
            'cpu': 2, 'mem': 4096, 'maxcpu': 4, 'maxmem': 8192
        }], 
        [
            {'node': 'node1', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768},
            {'node': 'node2', 'status': 'online', 'maxcpu': 16, 'maxmem': 32768}
        ]
    )
    assert result == {}, "Stopped VMs should not trigger rebalancing"
    
    print("✓ Edge cases passed")
    return True

if __name__ == '__main__':
    print("Testing proxmox_load_balance role filter...")
    print(f"Python path: {sys.path}")
    print(f"Filter path: {os.path.join(os.path.dirname(__file__), '..', 'plugins', 'filter')}")
    
    if test_load_balance_plan() and test_edge_cases():
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)
