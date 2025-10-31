#!/usr/bin/env python3
"""
Example usage of the Flipper marketplace scanner
"""

from scanner import MultiMarketplaceScanner, EbayScanner, AmazonScanner, WalmartScanner

# Create the scanner
scanner = MultiMarketplaceScanner()

# Add marketplaces to scan
scanner.add_scanner(EbayScanner())
scanner.add_scanner(AmazonScanner())
scanner.add_scanner(WalmartScanner())

# Example 1: Search all marketplaces
print("\n=== Example 1: Search all marketplaces ===")
results = scanner.scan_all("gaming mouse", max_results_per_marketplace=5)

for marketplace, products in results.items():
    print(f"\n{marketplace}:")
    for product in products:
        print(f"  - ${product.price:.2f}: {product.title}")

# Example 2: Find best deals
print("\n\n=== Example 2: Find best deals ===")
best_deals = scanner.find_best_deals(results=results)

print("\nTop 5 best deals:")
for i, product in enumerate(best_deals[:5], 1):
    print(f"{i}. ${product.price:.2f} - {product.title} [{product.marketplace}]")

# Example 3: Compare prices
print("\n\n=== Example 3: Compare average prices ===")
price_comparison = scanner.compare_prices(results=results)

print("\nAverage prices by marketplace:")
for marketplace, avg_price in sorted(price_comparison.items(), key=lambda x: x[1]):
    print(f"{marketplace:15} ${avg_price:.2f}")

# Example 4: Export results
print("\n\n=== Example 4: Export results ===")
scanner.export_results(results, "example_results.json")
print("Results exported successfully!")
