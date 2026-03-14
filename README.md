# Pokemon Card Price Bot

Finds Pokemon trading card listings on eBay Australia and Facebook Marketplace priced below recent sold prices, and monitors eBay auctions in real time — emailing you when a deal is about to end.

## How It Works

### Search Mode
1. **Scrapes sold prices** — Fetches recently sold listings on eBay AU to establish fair market value.
2. **Scrapes active listings** — Fetches current Buy It Now listings from eBay AU and/or Facebook Marketplace.
3. **Compares prices** — Groups cards by normalized title, computes average sold price, and flags listings significantly cheaper than market.

### Monitor Mode (Real-Time Auction Alerts)
1. **Continuously scans** eBay AU auctions sorted by ending soonest.
2. **Checks current bid** against the average sold price from recent sales history.
3. **Emails you** when an auction is within 1 hour of ending and the current bid is below market value — includes the listing URL and previous sale prices.

## Setup

```bash
pip install -r requirements.txt
```

### Email Configuration (for Monitor Mode)

Set your SMTP credentials so the bot can send alert emails. The easiest way is via environment variables:

```bash
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export EMAIL_FROM="your-email@gmail.com"
export ALERT_EMAIL_TO="davecannalonga@gmail.com"
```

For Gmail, you need an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

Alternatively, edit `config.py` directly.

## Usage

### Search for Deals (one-shot)

```bash
# Search both eBay AU and Facebook Marketplace
python bot.py search

# Search for a specific card
python bot.py search "Charizard VMAX"

# eBay only / Facebook only
python bot.py search "Pikachu" --source ebay
python bot.py search "Pikachu" --source facebook

# Custom threshold and price range
python bot.py search "Mewtwo GX" --threshold 30 --min-price 5 --max-price 100
```

### Monitor Auctions (real-time with email alerts)

```bash
# Monitor all Pokemon card auctions (default settings)
python bot.py monitor

# Monitor a specific card
python bot.py monitor "Charizard VMAX"

# Alert when auctions are 30 min from ending, check every 5 min
python bot.py monitor --alert-window 30 --interval 5

# Only alert on 30%+ discounts
python bot.py monitor "Pikachu" --threshold 30

# Override the alert email
python bot.py monitor --email someone@example.com
```

## Configuration

Edit `config.py` to change defaults:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEAL_THRESHOLD_PERCENT` | 20% | Minimum discount to qualify as a deal |
| `SOLD_LISTINGS_SAMPLE_SIZE` | 10 | Number of recent sales to average |
| `DEFAULT_MIN_PRICE` / `DEFAULT_MAX_PRICE` | $1 / $5000 | Price range filters |
| `MONITOR_ALERT_WINDOW_MINUTES` | 60 | Alert when auction ends within N minutes |
| `MONITOR_POLL_INTERVAL_MINUTES` | 10 | How often the monitor re-scans |
| `ALERT_EMAIL_TO` | davecannalonga@gmail.com | Email to receive alerts |
| `FB_SEARCH_LOCATIONS` | 8 AU cities | Cities to search on Facebook Marketplace |

## Email Alert Contents

Each alert email includes:
- Card name and current bid price
- Shipping cost and total price
- Number of bids and time remaining
- Average market price from recent sold data
- Discount percentage and dollar savings
- List of the last 10 individual sold prices
- Direct link to the eBay auction

## Disclaimer

This tool is for personal research purposes only. Always verify listing details before purchasing. Respect eBay's and Facebook's terms of service.
