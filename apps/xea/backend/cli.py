"""
Xea Governance Oracle - CLI Module

Command-line interface for evidence verification and other operations.

Usage:
    python -m backend.cli verify evidence.json
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="xea",
        description="Xea Governance Oracle CLI",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify an evidence bundle offline",
    )
    verify_parser.add_argument(
        "file",
        type=str,
        help="Path to evidence bundle JSON file",
    )
    verify_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed verification report",
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "verify":
        cmd_verify(args)
    else:
        parser.print_help()
        sys.exit(1)


def cmd_verify(args):
    """Handle verify command."""
    from app.replay import verify_file, verify_evidence_bundle, format_verification_report
    import json
    
    filepath = Path(args.file)
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    print(f"\n🔍 Verifying evidence bundle: {filepath.name}")
    print("─" * 50)
    
    # Load and verify
    try:
        with open(filepath, "r") as f:
            bundle = json.load(f)
        
        result = verify_evidence_bundle(bundle)
        
        if args.verbose:
            print(format_verification_report(result))
        else:
            # Simple output
            if result.is_valid:
                print("✅ Claims hash:      MATCH")
                print("✅ Responses hash:   MATCH")
                print("✅ Aggregation hash: MATCH")
                print("✅ Computation hash: MATCH")
                print("")
                print("🎉 Evidence bundle verified successfully!")
                print(f"   Hash: {result.computed_hash}")
            else:
                print("❌ Verification FAILED")
                print(f"   Expected: {result.expected_hash}")
                print(f"   Computed: {result.computed_hash}")
                for error in result.errors:
                    print(f"   Error: {error}")
                sys.exit(1)
                
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in file: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
