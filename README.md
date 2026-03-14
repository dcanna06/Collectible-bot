# Pokemon Card Price Bot

Finds Pokemon trading card listings on eBay Australia that are priced below recent sold prices — i.e. cards selling below market value.

## How It Works

1. **Scrapes sold prices** — Fetches recently completed/sold listings on eBay AU for your search query to establish a fair market price.
2. **Scrapes active listings** — Fetches current Buy It Now listings located in Australia.
3. **Compares prices** — Groups cards by normalized title, computes average sold price, and flags active listings that are significantly cheaper than the market average.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Default search (broad "Pokemon card")
python bot.py

# Search for a specific card
python bot.py "Charizard VMAX"

# Only show listings 30%+ below market value
python bot.py "Pikachu" --threshold 30

# Filter by price range
python bot.py "Mewtwo GX" --min-price 5 --max-price 100

# Fetch more pages for deeper search
python bot.py "Umbreon" --sold-pages 4 --listing-pages 5
```

## Configuration

Edit `config.py` to change defaults:

- `DEAL_THRESHOLD_PERCENT` — Minimum discount to qualify as a deal (default: 20%)
- `SOLD_LISTINGS_SAMPLE_SIZE` — Number of recent sales to average (default: 10)
- `DEFAULT_MIN_PRICE` / `DEFAULT_MAX_PRICE` — Price range filters
- `REQUEST_DELAY` — Delay between requests (be respectful to eBay's servers)

## Output

The bot displays a table of deals sorted by discount percentage, including:
- Card name
- Current listing price (including shipping)
- Average market price (from sold data)
- Discount percentage and dollar savings
- Direct links to each listing

## Disclaimer

This tool is for personal research purposes only. Always verify listing details before purchasing. Respect eBay's terms of service.
