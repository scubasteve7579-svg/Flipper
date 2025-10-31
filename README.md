# Flipper
Multi Marketplace Scanner

A tool for scanning multiple online marketplaces to find profitable items for reselling.

## Features

- Scan multiple marketplaces simultaneously
- Configurable search criteria
- Easy-to-extend architecture for adding new marketplaces
- CLI interface for quick scans

## Usage

```bash
python flipper.py --search "vintage camera" --marketplaces ebay amazon
```

## Supported Marketplaces

- eBay
- Amazon
- Facebook Marketplace

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `config.json` file with your marketplace API credentials and preferences.

Example:
```json
{
  "ebay": {
    "enabled": true,
    "api_key": "your_api_key"
  },
  "amazon": {
    "enabled": true,
    "api_key": "your_api_key"
  },
  "facebook": {
    "enabled": true
  }
}
```
