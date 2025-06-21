"""
Stats command module for viewing network statistics
"""

def get_stats(network="mainnet"):
    """
    Get statistics for the specified network
    
    Args:
        network (str): The network to check (mainnet, testnet)
    """
    print(f"Fetching statistics for {network} network...")
    
    # This is where you would implement the actual API call to get network stats
    # For this template, we'll just print some example output
    
    print("\n=== Network Statistics ===")
    print(f"Network:           {network}")
    print(f"Active Nodes:      1,245")
    print(f"Total Stake:       24.5M CTR")
    print(f"Block Height:      8,762,103")
    print(f"TPS (avg):         156.3")
    print(f"Daily Inferences:  5.2M")
    print(f"Network Health:    98.2%")
    print("=========================\n")
