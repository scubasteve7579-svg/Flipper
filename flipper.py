#!/usr/bin/env python3
"""
Flipper - Multi Marketplace Scanner
Main CLI interface for scanning multiple marketplaces
"""
import argparse
import json
from multi_scanner import MultiMarketplaceScanner


def print_results(results):
    """
    Pretty print the scan results.
    
    Args:
        results: Dictionary of marketplace results
    """
    print("\n" + "="*80)
    print("SCAN RESULTS")
    print("="*80)
    
    total_items = sum(len(items) for items in results.values())
    
    if total_items == 0:
        print("\nNo items found.")
        return
    
    for marketplace, items in results.items():
        if not items:
            continue
            
        print(f"\n{marketplace} ({len(items)} items):")
        print("-" * 80)
        
        for i, item in enumerate(items, 1):
            print(f"\n  {i}. {item.get('title', 'N/A')}")
            print(f"     Price: ${item.get('price', 'N/A')}")
            print(f"     URL: {item.get('url', 'N/A')}")
            
            # Print marketplace-specific fields
            for key, value in item.items():
                if key not in ['title', 'price', 'url', 'marketplace']:
                    print(f"     {key.capitalize()}: {value}")
    
    print("\n" + "="*80)
    print(f"Total items found: {total_items}")
    print("="*80 + "\n")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Flipper - Multi Marketplace Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --search "vintage camera"
  %(prog)s --search "laptop" --marketplaces ebay amazon
  %(prog)s --search "phone" --config my_config.json
  %(prog)s --list-marketplaces
        """
    )
    
    parser.add_argument(
        '--search', '-s',
        type=str,
        help='Search query to look for across marketplaces'
    )
    
    parser.add_argument(
        '--marketplaces', '-m',
        nargs='+',
        help='Specific marketplaces to scan (e.g., ebay amazon facebook)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    
    parser.add_argument(
        '--list-marketplaces', '-l',
        action='store_true',
        help='List all available marketplaces'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Save results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Initialize the scanner
    scanner = MultiMarketplaceScanner(args.config)
    
    # List marketplaces if requested
    if args.list_marketplaces:
        marketplaces = scanner.get_enabled_marketplaces()
        print("\nEnabled Marketplaces:")
        for mp in marketplaces:
            print(f"  - {mp}")
        print()
        return
    
    # Require search query if not listing marketplaces
    if not args.search:
        parser.error("--search is required unless using --list-marketplaces")
    
    # Perform the scan
    print(f"\nSearching for: '{args.search}'")
    if args.marketplaces:
        print(f"Marketplaces: {', '.join(args.marketplaces)}")
    else:
        print("Marketplaces: All enabled")
    print()
    
    results = scanner.scan_all(args.search, args.marketplaces)
    
    # Print results
    print_results(results)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == '__main__':
    main()
