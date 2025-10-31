# Flipper
Multi-marketplace scanner for finding the best deals across online marketplaces.

## Overview
Flipper scans multiple online marketplaces (eBay, Amazon, Walmart, etc.) to help you find the best prices and arbitrage opportunities for products.

## Features
- **Multi-marketplace scanning**: Search across multiple platforms simultaneously
- **Price comparison**: Compare average prices across different marketplaces
- **Best deals finder**: Automatically find the lowest prices
- **Export results**: Save scan results to JSON for further analysis
- **Extensible architecture**: Easy to add new marketplace scanners

## Installation

```bash
# Clone the repository
git clone https://github.com/scubasteve7579-svg/Flipper.git
cd Flipper

# Install dependencies (optional, basic version has no external dependencies)
pip install -r requirements.txt
```

## Usage

### Basic Usage
Run the scanner with default settings:
```bash
python scanner.py
```

### Programmatic Usage
```python
from scanner import MultiMarketplaceScanner, EbayScanner, AmazonScanner

# Create scanner
scanner = MultiMarketplaceScanner()

# Add marketplaces
scanner.add_scanner(EbayScanner())
scanner.add_scanner(AmazonScanner())

# Search for products
results = scanner.scan_all("laptop", max_results_per_marketplace=10)

# Find best deals
best_deals = scanner.find_best_deals("laptop")

# Compare prices
price_comparison = scanner.compare_prices("laptop")
```

## Configuration
Edit `config.json` to customize:
- Maximum results per marketplace
- Default search queries
- Enable/disable specific marketplaces
- API keys for marketplace integrations

## Supported Marketplaces
- ✓ eBay
- ✓ Amazon
- ✓ Walmart

## Future Enhancements
- Real API integrations (currently using mock data)
- Web scraping support
- Price history tracking
- Alert system for price drops
- GUI interface

## License
MIT License
