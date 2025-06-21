"""
Status command module for checking node status
"""

def check_status(node_id):
    """
    Check the status of a specific node
    
    Args:
        node_id (str): The ID of the node to check
    """
    print(f"Checking status for node: {node_id}")
    
    # This is where you would implement the actual API call to check node status
    # For this template, we'll just print some example output
    
    print("\n=== Node Status ===")
    print(f"Node ID:       {node_id}")
    print(f"Status:        Active")
    print(f"Uptime:        14 days, 6 hours")
    print(f"Version:       v2.4.1")
    print(f"Stake:         15,000 CTR")
    print(f"Success Rate:  98.7%")
    print(f"Last Ping:     2 minutes ago")
    print("===================\n")
