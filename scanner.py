#!/usr/bin/env python3
"""
Flipper - Multi-Marketplace Scanner
Scans multiple online marketplaces for product deals and arbitrage opportunities.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class Product:
    """Represents a product found on a marketplace"""
    
    def __init__(self, title: str, price: float, url: str, marketplace: str, 
                 condition: str = "new", seller: str = ""):
        self.title = title
        self.price = price
        self.url = url
        self.marketplace = marketplace
        self.condition = condition
        self.seller = seller
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary"""
        return {
            "title": self.title,
            "price": self.price,
            "url": self.url,
            "marketplace": self.marketplace,
            "condition": self.condition,
            "seller": self.seller,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __repr__(self):
        return f"Product({self.title}, ${self.price}, {self.marketplace})"


class MarketplaceScanner(ABC):
    """Abstract base class for marketplace scanners"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[Product]:
        """Search the marketplace for products matching the query"""
        pass
    
    @abstractmethod
    def get_product_details(self, product_id: str) -> Product:
        """Get detailed information about a specific product"""
        pass


class EbayScanner(MarketplaceScanner):
    """Scanner for eBay marketplace"""
    
    def __init__(self):
        super().__init__("eBay")
    
    def search(self, query: str, max_results: int = 10) -> List[Product]:
        """Search eBay for products (mock implementation)"""
        print(f"[{self.name}] Searching for: {query}")
        
        # Mock data - in production, this would use eBay API
        products = []
        for i in range(min(max_results, 3)):
            product = Product(
                title=f"{query} - eBay Item {i+1}",
                price=19.99 + (i * 5),
                url=f"https://ebay.com/item/{i+1}",
                marketplace=self.name,
                condition="used" if i % 2 == 0 else "new",
                seller=f"seller_{i+1}"
            )
            products.append(product)
        
        return products
    
    def get_product_details(self, product_id: str) -> Product:
        """Get eBay product details (mock implementation)"""
        return Product(
            title=f"eBay Product {product_id}",
            price=29.99,
            url=f"https://ebay.com/item/{product_id}",
            marketplace=self.name,
            condition="used",
            seller="example_seller"
        )


class AmazonScanner(MarketplaceScanner):
    """Scanner for Amazon marketplace"""
    
    def __init__(self):
        super().__init__("Amazon")
    
    def search(self, query: str, max_results: int = 10) -> List[Product]:
        """Search Amazon for products (mock implementation)"""
        print(f"[{self.name}] Searching for: {query}")
        
        # Mock data - in production, this would use Amazon Product Advertising API
        products = []
        for i in range(min(max_results, 3)):
            product = Product(
                title=f"{query} - Amazon Product {i+1}",
                price=24.99 + (i * 7),
                url=f"https://amazon.com/dp/ASIN{i+1}",
                marketplace=self.name,
                condition="new",
                seller="Amazon" if i == 0 else f"ThirdParty_{i}"
            )
            products.append(product)
        
        return products
    
    def get_product_details(self, product_id: str) -> Product:
        """Get Amazon product details (mock implementation)"""
        return Product(
            title=f"Amazon Product {product_id}",
            price=34.99,
            url=f"https://amazon.com/dp/{product_id}",
            marketplace=self.name,
            condition="new",
            seller="Amazon"
        )


class WalmartScanner(MarketplaceScanner):
    """Scanner for Walmart marketplace"""
    
    def __init__(self):
        super().__init__("Walmart")
    
    def search(self, query: str, max_results: int = 10) -> List[Product]:
        """Search Walmart for products (mock implementation)"""
        print(f"[{self.name}] Searching for: {query}")
        
        # Mock data - in production, this would use Walmart API
        products = []
        for i in range(min(max_results, 3)):
            product = Product(
                title=f"{query} - Walmart Item {i+1}",
                price=17.99 + (i * 4),
                url=f"https://walmart.com/ip/{i+1}",
                marketplace=self.name,
                condition="new",
                seller="Walmart"
            )
            products.append(product)
        
        return products
    
    def get_product_details(self, product_id: str) -> Product:
        """Get Walmart product details (mock implementation)"""
        return Product(
            title=f"Walmart Product {product_id}",
            price=27.99,
            url=f"https://walmart.com/ip/{product_id}",
            marketplace=self.name,
            condition="new",
            seller="Walmart"
        )


class MultiMarketplaceScanner:
    """Orchestrates scanning across multiple marketplaces"""
    
    def __init__(self):
        self.scanners: List[MarketplaceScanner] = []
    
    def add_scanner(self, scanner: MarketplaceScanner):
        """Add a marketplace scanner"""
        self.scanners.append(scanner)
        print(f"Added scanner: {scanner.name}")
    
    def scan_all(self, query: str, max_results_per_marketplace: int = 10) -> Dict[str, List[Product]]:
        """Scan all registered marketplaces"""
        print(f"\n{'='*60}")
        print(f"Scanning {len(self.scanners)} marketplaces for: '{query}'")
        print(f"{'='*60}\n")
        
        results = {}
        for scanner in self.scanners:
            try:
                products = scanner.search(query, max_results_per_marketplace)
                results[scanner.name] = products
                print(f"  ✓ Found {len(products)} products on {scanner.name}")
            except Exception as e:
                print(f"  ✗ Error scanning {scanner.name}: {e}")
                results[scanner.name] = []
        
        return results
    
    def find_best_deals(self, query: str, max_results_per_marketplace: int = 10) -> List[Product]:
        """Find the best deals across all marketplaces"""
        all_results = self.scan_all(query, max_results_per_marketplace)
        
        # Flatten all products
        all_products = []
        for products in all_results.values():
            all_products.extend(products)
        
        # Sort by price
        all_products.sort(key=lambda p: p.price)
        
        return all_products
    
    def compare_prices(self, query: str) -> Dict[str, float]:
        """Compare average prices across marketplaces"""
        all_results = self.scan_all(query)
        
        price_comparison = {}
        for marketplace, products in all_results.items():
            if products:
                avg_price = sum(p.price for p in products) / len(products)
                price_comparison[marketplace] = round(avg_price, 2)
        
        return price_comparison
    
    def export_results(self, results: Dict[str, List[Product]], filename: str = "scan_results.json"):
        """Export scan results to JSON file"""
        export_data = {}
        for marketplace, products in results.items():
            export_data[marketplace] = [p.to_dict() for p in products]
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\nResults exported to: {filename}")


def main():
    """Main entry point for the scanner"""
    print("\n" + "="*60)
    print("FLIPPER - Multi-Marketplace Scanner")
    print("="*60 + "\n")
    
    # Initialize the multi-marketplace scanner
    scanner = MultiMarketplaceScanner()
    
    # Add marketplace scanners
    scanner.add_scanner(EbayScanner())
    scanner.add_scanner(AmazonScanner())
    scanner.add_scanner(WalmartScanner())
    
    # Example search query
    search_query = "wireless headphones"
    
    # Scan all marketplaces
    results = scanner.scan_all(search_query, max_results_per_marketplace=5)
    
    # Show best deals
    print(f"\n{'='*60}")
    print("BEST DEALS (sorted by price)")
    print(f"{'='*60}\n")
    
    best_deals = scanner.find_best_deals(search_query, max_results_per_marketplace=5)
    for i, product in enumerate(best_deals[:10], 1):
        print(f"{i}. ${product.price:.2f} - {product.title}")
        print(f"   [{product.marketplace}] {product.url}\n")
    
    # Compare average prices
    print(f"\n{'='*60}")
    print("PRICE COMPARISON (average prices)")
    print(f"{'='*60}\n")
    
    price_comparison = scanner.compare_prices(search_query)
    for marketplace, avg_price in sorted(price_comparison.items(), key=lambda x: x[1]):
        print(f"{marketplace:15} ${avg_price:.2f}")
    
    # Export results
    scanner.export_results(results)
    
    print(f"\n{'='*60}")
    print("Scan complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
