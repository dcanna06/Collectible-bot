# Pokemon Card Price Bot

Finds Pokemon trading card listings on eBay Australia and Facebook Marketplace that are priced below recent sold prices — i.e. cards selling below market value.

## How It Works

1. **Scrapes sold prices** — Fetches recently completed/sold listings on eBay AU to establish a fair market price.
2. **Scrapes active listings** — Fetches current Buy It Now listings from eBay AU and/or Facebook Marketplace across Australian cities.
3. **Compares prices** — Groups cards by normalized title, computes average sold price, and flags active listings that are significantly cheaper than the market average.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Default: search both eBay AU and Facebook Marketplace
python bot.py

# Search for a specific card
python bot.py "Charizard VMAX"

# Search only eBay
python bot.py "Pikachu" --source ebay

# Search only Facebook Marketplace
python bot.py "Pikachu" --source facebook

# Only show listings 30%+ below market value
python bot.py "Pikachu" --threshold 30

# Filter by price range
python bot.py "Mewtwo GX" --min-price 5 --max-price 100

# Fetch more eBay pages for deeper search
python bot.py "Umbreon" --sold-pages 4 --listing-pages 5

# Search specific Facebook Marketplace locations
python bot.py "Charizard" --source facebook --fb-locations sydney melbourne
```

## Configuration

Edit `config.py` to change defaults:

- `DEAL_THRESHOLD_PERCENT` — Minimum discount to qualify as a deal (default: 20%)
- `SOLD_LISTINGS_SAMPLE_SIZE` — Number of recent sales to average (default: 10)
- `DEFAULT_MIN_PRICE` / `DEFAULT_MAX_PRICE` — Price range filters
- `REQUEST_DELAY` — Delay between eBay requests
- `FB_REQUEST_DELAY` — Delay between Facebook requests
- `FB_SEARCH_LOCATIONS` — List of Australian cities to search on Facebook Marketplace

## Output

The bot displays a table of deals sorted by discount percentage, including:
- Source platform (eBay or FB)
- Card name
- Current listing price (eBay includes shipping; FB is typically local pickup)
- Average market price (from eBay AU sold data)
- Discount percentage and dollar savings
- Direct links to each listing, grouped by platform

## Disclaimer

This tool is for personal research purposes only. Always verify listing details before purchasing. Respect eBay's and Facebook's terms of service.
