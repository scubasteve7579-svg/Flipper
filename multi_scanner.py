"""
Multi-Marketplace Scanner Orchestrator
Coordinates scanning across multiple marketplaces
"""
import json
from typing import List, Dict, Any
from scanner_base import MarketplaceScanner
from ebay_scanner import EbayScanner
from amazon_scanner import AmazonScanner
from facebook_scanner import FacebookScanner


class MultiMarketplaceScanner:
    """
    Orchestrates scanning across multiple marketplaces.
    """
    
    def __init__(self, config_path: str = 'config.json'):
        """
        Initialize the multi-marketplace scanner.
        
        Args:
            config_path: Path to the configuration file
        """
        self.scanners: List[MarketplaceScanner] = []
        self.load_config(config_path)
        
    def load_config(self, config_path: str):
        """
        Load configuration and initialize scanners.
        
        Args:
            config_path: Path to the configuration file
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file '{config_path}' not found. Using default settings.")
            config = {
                'ebay': {'enabled': True, 'max_results': 10},
                'amazon': {'enabled': True, 'max_results': 10},
                'facebook': {'enabled': True, 'max_results': 10}
            }
        
        # Initialize scanners based on configuration
        if config.get('ebay', {}).get('enabled', True):
            self.scanners.append(EbayScanner(config.get('ebay', {})))
        
        if config.get('amazon', {}).get('enabled', True):
            self.scanners.append(AmazonScanner(config.get('amazon', {})))
        
        if config.get('facebook', {}).get('enabled', True):
            self.scanners.append(FacebookScanner(config.get('facebook', {})))
    
    def scan_all(self, query: str, marketplaces: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan all enabled marketplaces for the given query.
        
        Args:
            query: Search query string
            marketplaces: Optional list of specific marketplace names to scan.
                         If None, scans all enabled marketplaces.
        
        Returns:
            Dictionary mapping marketplace names to lists of results
        """
        results = {}
        
        for scanner in self.scanners:
            if not scanner.is_enabled():
                continue
            
            marketplace_name = scanner.get_marketplace_name()
            
            # If specific marketplaces are requested, only scan those
            if marketplaces:
                # Check if any requested marketplace name is contained in the scanner's name
                # (e.g., "facebook" matches "Facebook Marketplace")
                marketplace_match = any(
                    m.lower() in marketplace_name.lower() or marketplace_name.lower() in m.lower()
                    for m in marketplaces
                )
                if not marketplace_match:
                    continue
            
            print(f"Scanning {marketplace_name}...")
            try:
                items = scanner.search(query)
                results[marketplace_name] = items
                print(f"  Found {len(items)} items on {marketplace_name}")
            except Exception as e:
                print(f"  Error scanning {marketplace_name}: {e}")
                results[marketplace_name] = []
        
        return results
    
    def get_enabled_marketplaces(self) -> List[str]:
        """
        Get list of enabled marketplace names.
        
        Returns:
            List of marketplace names
        """
        return [scanner.get_marketplace_name() for scanner in self.scanners if scanner.is_enabled()]
