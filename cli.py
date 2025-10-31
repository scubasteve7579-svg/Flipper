#!/usr/bin/env python3
"""
CLI interface for Flipper marketplace scanner
"""

import sys
import argparse
from scanner import MultiMarketplaceScanner, EbayScanner, AmazonScanner, WalmartScanner


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Flipper - Multi-Marketplace Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search "laptop"
  %(prog)s search "gaming mouse" --max 20
  %(prog)s compare "wireless headphones"
  %(prog)s deals "mechanical keyboard" --top 5
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search across all marketplaces')
    search_parser.add_argument('query', type=str, help='Search query')
    search_parser.add_argument('--max', type=int, default=10, help='Max results per marketplace (default: 10)')
    search_parser.add_argument('--export', type=str, help='Export results to file')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare prices across marketplaces')
    compare_parser.add_argument('query', type=str, help='Search query')
    
    # Deals command
    deals_parser = subparsers.add_parser('deals', help='Find best deals')
    deals_parser.add_argument('query', type=str, help='Search query')
    deals_parser.add_argument('--top', type=int, default=10, help='Show top N deals (default: 10)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize scanner
    scanner = MultiMarketplaceScanner()
    scanner.add_scanner(EbayScanner())
    scanner.add_scanner(AmazonScanner())
    scanner.add_scanner(WalmartScanner())
    
    # Execute command
    if args.command == 'search':
        results = scanner.scan_all(args.query, args.max)
        
        print(f"\n{'='*60}")
        print(f"SEARCH RESULTS")
        print(f"{'='*60}\n")
        
        for marketplace, products in results.items():
            print(f"\n{marketplace} ({len(products)} results):")
            for i, product in enumerate(products, 1):
                print(f"  {i}. ${product.price:.2f} - {product.title}")
                print(f"     {product.url}")
        
        if args.export:
            scanner.export_results(results, args.export)
    
    elif args.command == 'compare':
        price_comparison = scanner.compare_prices(args.query)
        
        print(f"\n{'='*60}")
        print(f"PRICE COMPARISON")
        print(f"{'='*60}\n")
        
        for marketplace, avg_price in sorted(price_comparison.items(), key=lambda x: x[1]):
            print(f"{marketplace:15} ${avg_price:.2f}")
    
    elif args.command == 'deals':
        best_deals = scanner.find_best_deals(args.query)
        
        print(f"\n{'='*60}")
        print(f"BEST DEALS (Top {args.top})")
        print(f"{'='*60}\n")
        
        for i, product in enumerate(best_deals[:args.top], 1):
            print(f"{i}. ${product.price:.2f} - {product.title}")
            print(f"   [{product.marketplace}] {product.url}\n")


if __name__ == "__main__":
    main()
