#!/usr/bin/env python3
"""
Cortensor Hello World Tool - CLI Interface
A template CLI tool for interacting with Cortensor networks
"""

import argparse
import sys
import os
from .commands import status, stats, wallet

def main():
    """Main entry point for the CLI tool"""
    parser = argparse.ArgumentParser(
        description="Cortensor Hello World Tool - A template CLI for Cortensor network interaction"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check node status")
    status_parser.add_argument("--node-id", required=True, help="Node ID to check")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="View network statistics")
    stats_parser.add_argument("--network", default="mainnet", help="Network to check (mainnet, testnet)")
    
    # Wallet command
    wallet_parser = subparsers.add_parser("wallet", help="Wallet management")
    wallet_parser.add_argument("--create", action="store_true", help="Create a new wallet")
    wallet_parser.add_argument("--balance", action="store_true", help="Check wallet balance")
    
    args = parser.parse_args()
    
    if args.command == "status":
        status.check_status(args.node_id)
    elif args.command == "stats":
        stats.get_stats(args.network)
    elif args.command == "wallet":
        if args.create:
            wallet.create_wallet()
        elif args.balance:
            wallet.check_balance()
        else:
            wallet.show_info()
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
