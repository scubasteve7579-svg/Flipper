# Flipper - Quick Start Guide

## Installation

1. Clone the repository:
```bash
git clone https://github.com/scubasteve7579-svg/Flipper.git
cd Flipper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your marketplaces:
```bash
cp config.example.json config.json
# Edit config.json with your API keys and preferences
```

## Basic Usage

### List available marketplaces
```bash
python3 flipper.py --list-marketplaces
```

### Search all marketplaces
```bash
python3 flipper.py --search "vintage camera"
```

### Search specific marketplaces
```bash
python3 flipper.py --search "laptop" --marketplaces ebay amazon
```

### Save results to JSON
```bash
python3 flipper.py --search "phone" --output results.json
```

### Use custom configuration
```bash
python3 flipper.py --search "watch" --config my_config.json
```

## Command-Line Options

- `--search, -s` - Search query (required unless using --list-marketplaces)
- `--marketplaces, -m` - Specific marketplaces to scan (optional)
- `--config, -c` - Path to configuration file (default: config.json)
- `--list-marketplaces, -l` - List all available marketplaces
- `--output, -o` - Save results to JSON file
- `--help, -h` - Show help message

## Examples

### Example 1: Search for vintage cameras on eBay only
```bash
python3 flipper.py --search "vintage camera" --marketplaces ebay
```

### Example 2: Search for laptops on eBay and Amazon
```bash
python3 flipper.py --search "laptop" --marketplaces ebay amazon
```

### Example 3: Search all marketplaces and save to file
```bash
python3 flipper.py --search "gaming console" --output scan_results.json
```

## Adding New Marketplaces

To add a new marketplace scanner:

1. Create a new scanner class inheriting from `MarketplaceScanner`
2. Implement `get_marketplace_name()` and `search()` methods
3. Add the scanner to `multi_scanner.py` in the `load_config()` method
4. Add configuration for the new marketplace in `config.json`

Example:
```python
from scanner_base import MarketplaceScanner

class NewMarketplaceScanner(MarketplaceScanner):
    def get_marketplace_name(self):
        return "New Marketplace"
    
    def search(self, query):
        # Implement your API calls here
        return []
```

## Configuration

The `config.json` file controls which marketplaces are enabled and their settings:

```json
{
  "ebay": {
    "enabled": true,
    "api_key": "your_key",
    "max_results": 10
  },
  "amazon": {
    "enabled": true,
    "api_key": "your_key",
    "max_results": 10
  },
  "facebook": {
    "enabled": true,
    "max_results": 10
  }
}
```

## Notes

- Current implementation uses mock data for demonstration
- To use real marketplace APIs, you need to:
  1. Obtain API keys from each marketplace
  2. Update the scanner implementations to make actual API calls
  3. Add your API keys to config.json

## Support

For issues or questions, please create an issue in the GitHub repository.
