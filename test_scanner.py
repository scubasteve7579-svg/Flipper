"""
Unit tests for Multi-Marketplace Scanner
"""
import unittest
import json
import os
from scanner_base import MarketplaceScanner
from ebay_scanner import EbayScanner
from amazon_scanner import AmazonScanner
from facebook_scanner import FacebookScanner
from multi_scanner import MultiMarketplaceScanner


class TestMarketplaceScanners(unittest.TestCase):
    """Test individual marketplace scanners."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            'enabled': True,
            'max_results': 5
        }
    
    def test_ebay_scanner_name(self):
        """Test eBay scanner returns correct name."""
        scanner = EbayScanner(self.config)
        self.assertEqual(scanner.get_marketplace_name(), "eBay")
    
    def test_ebay_scanner_search(self):
        """Test eBay scanner search returns results."""
        scanner = EbayScanner(self.config)
        results = scanner.search("test query")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('title', results[0])
        self.assertIn('price', results[0])
        self.assertIn('url', results[0])
    
    def test_amazon_scanner_name(self):
        """Test Amazon scanner returns correct name."""
        scanner = AmazonScanner(self.config)
        self.assertEqual(scanner.get_marketplace_name(), "Amazon")
    
    def test_amazon_scanner_search(self):
        """Test Amazon scanner search returns results."""
        scanner = AmazonScanner(self.config)
        results = scanner.search("test query")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('title', results[0])
        self.assertIn('price', results[0])
    
    def test_facebook_scanner_name(self):
        """Test Facebook scanner returns correct name."""
        scanner = FacebookScanner(self.config)
        self.assertEqual(scanner.get_marketplace_name(), "Facebook Marketplace")
    
    def test_facebook_scanner_search(self):
        """Test Facebook scanner search returns results."""
        scanner = FacebookScanner(self.config)
        results = scanner.search("test query")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('title', results[0])
        self.assertIn('price', results[0])
    
    def test_scanner_enabled(self):
        """Test scanner enabled flag."""
        scanner = EbayScanner({'enabled': True})
        self.assertTrue(scanner.is_enabled())
        
        scanner_disabled = EbayScanner({'enabled': False})
        self.assertFalse(scanner_disabled.is_enabled())
    
    def test_max_results_limit(self):
        """Test that max_results limits the number of results."""
        config = {'enabled': True, 'max_results': 2}
        scanner = EbayScanner(config)
        results = scanner.search("test")
        self.assertLessEqual(len(results), 2)


class TestMultiMarketplaceScanner(unittest.TestCase):
    """Test the multi-marketplace scanner orchestrator."""
    
    def setUp(self):
        """Set up test configuration file."""
        self.test_config = {
            'ebay': {'enabled': True, 'max_results': 5},
            'amazon': {'enabled': True, 'max_results': 5},
            'facebook': {'enabled': True, 'max_results': 5}
        }
        self.config_file = '/tmp/test_config.json'
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test configuration file."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
    
    def test_load_config(self):
        """Test configuration loading."""
        scanner = MultiMarketplaceScanner(self.config_file)
        self.assertEqual(len(scanner.scanners), 3)
    
    def test_get_enabled_marketplaces(self):
        """Test getting list of enabled marketplaces."""
        scanner = MultiMarketplaceScanner(self.config_file)
        marketplaces = scanner.get_enabled_marketplaces()
        self.assertEqual(len(marketplaces), 3)
        self.assertIn("eBay", marketplaces)
        self.assertIn("Amazon", marketplaces)
        self.assertIn("Facebook Marketplace", marketplaces)
    
    def test_scan_all(self):
        """Test scanning all marketplaces."""
        scanner = MultiMarketplaceScanner(self.config_file)
        results = scanner.scan_all("test query")
        self.assertEqual(len(results), 3)
        self.assertIn("eBay", results)
        self.assertIn("Amazon", results)
        self.assertIn("Facebook Marketplace", results)
    
    def test_scan_specific_marketplace(self):
        """Test scanning specific marketplace."""
        scanner = MultiMarketplaceScanner(self.config_file)
        results = scanner.scan_all("test query", ["ebay"])
        self.assertEqual(len(results), 1)
        self.assertIn("eBay", results)
    
    def test_scan_multiple_specific_marketplaces(self):
        """Test scanning multiple specific marketplaces."""
        scanner = MultiMarketplaceScanner(self.config_file)
        results = scanner.scan_all("test query", ["ebay", "amazon"])
        self.assertEqual(len(results), 2)
        self.assertIn("eBay", results)
        self.assertIn("Amazon", results)
        self.assertNotIn("Facebook Marketplace", results)
    
    def test_flexible_marketplace_matching(self):
        """Test flexible marketplace name matching."""
        scanner = MultiMarketplaceScanner(self.config_file)
        # "facebook" should match "Facebook Marketplace"
        results = scanner.scan_all("test query", ["facebook"])
        self.assertEqual(len(results), 1)
        self.assertIn("Facebook Marketplace", results)


if __name__ == '__main__':
    unittest.main()
