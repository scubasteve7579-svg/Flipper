"""
Base Scanner Class for Multi-Marketplace Scanner
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class MarketplaceScanner(ABC):
    """
    Abstract base class for marketplace scanners.
    Each marketplace implementation should inherit from this class.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scanner with configuration.
        
        Args:
            config: Dictionary containing marketplace-specific configuration
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.max_results = config.get('max_results', 10)
        
    @abstractmethod
    def get_marketplace_name(self) -> str:
        """
        Return the name of the marketplace.
        
        Returns:
            str: Name of the marketplace
        """
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for items in the marketplace.
        
        Args:
            query: Search query string
            
        Returns:
            List of dictionaries containing item information
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if this scanner is enabled.
        
        Returns:
            bool: True if enabled, False otherwise
        """
        return self.enabled
