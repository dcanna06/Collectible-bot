#!/usr/bin/env python3
"""Pokemon Card Price Bot – finds undervalued Pokemon card listings on eBay Australia.

Usage:
    python bot.py                          # Search with defaults
    python bot.py "Charizard VMAX"         # Search for a specific card
    python bot.py --threshold 30           # Only show 30%+ below market
    python bot.py --min-price 5 --max-price 200  # Price range filter
"""

import argparse
import sys

from tabulate import tabulate

import config
from scraper import fetch_sold_prices, fetch_active_listings
from analyzer import compute_market_prices, find_deals


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find Pokemon cards listed below market value on eBay Australia."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=config.DEFAULT_SEARCH_QUERY,
        help=f"Search query (default: '{config.DEFAULT_SEARCH_QUERY}')",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=config.DEAL_THRESHOLD_PERCENT,
        help=f"Minimum discount %% to show (default: {config.DEAL_THRESHOLD_PERCENT}%%)",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=config.DEFAULT_MIN_PRICE,
        help=f"Minimum listing price in AUD (default: {config.DEFAULT_MIN_PRICE})",
    )
    parser.add_argument(
        "--max-price",
        type=float,
        default=config.DEFAULT_MAX_PRICE,
        help=f"Maximum listing price in AUD (default: {config.DEFAULT_MAX_PRICE})",
    )
    parser.add_argument(
        "--sold-pages",
        type=int,
        default=2,
        help="Number of sold listing pages to fetch (default: 2)",
    )
    parser.add_argument(
        "--listing-pages",
        type=int,
        default=3,
        help="Number of active listing pages to fetch (default: 3)",
    )
    return parser.parse_args()


def run(query, threshold, min_price, max_price, sold_pages, listing_pages):
    """Run the full pipeline: scrape, analyze, and return deals."""

    # Temporarily override config prices
    config.DEFAULT_MIN_PRICE = min_price
    config.DEFAULT_MAX_PRICE = max_price

    # Step 1: Fetch sold prices
    print(f"\n[1/3] Fetching recent sold prices for: \"{query}\" ...")
    sold = fetch_sold_prices(query, max_pages=sold_pages)
    print(f"      Found {len(sold)} sold listings.")

    if not sold:
        print("\n  No sold data found. Try a more specific search query.")
        return []

    # Step 2: Fetch active listings
    print(f"\n[2/3] Fetching active listings in Australia for: \"{query}\" ...")
    active = fetch_active_listings(query, max_pages=listing_pages)
    print(f"      Found {len(active)} active listings.")

    if not active:
        print("\n  No active listings found.")
        return []

    # Step 3: Find deals
    print(f"\n[3/3] Analyzing for deals (>= {threshold}% below market) ...")
    market = compute_market_prices(sold)
    deals = find_deals(active, market, threshold_percent=threshold)

    return deals


def display_deals(deals):
    """Print deals in a formatted table."""
    if not deals:
        print("\n  No deals found matching your criteria.")
        print("  Try broadening your search or lowering the discount threshold.")
        return

    print(f"\n{'=' * 80}")
    print(f"  DEALS FOUND: {len(deals)} listings below market value")
    print(f"{'=' * 80}\n")

    table_data = []
    for i, deal in enumerate(deals, 1):
        title = deal["title"]
        if len(title) > 50:
            title = title[:47] + "..."
        table_data.append([
            i,
            title,
            f"${deal['listing_price']:.2f}",
            f"${deal['market_price']:.2f}",
            f"-{deal['discount_percent']}%",
            f"${deal['savings']:.2f}",
        ])

    headers = ["#", "Card", "Price", "Market", "Discount", "Savings"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Print URLs separately for easy clicking
    print(f"\n{'─' * 80}")
    print("  LINKS:\n")
    for i, deal in enumerate(deals, 1):
        print(f"  {i}. {deal['url']}")

    print()


def main():
    args = parse_args()

    print("=" * 80)
    print("  POKEMON CARD PRICE BOT – eBay Australia Deal Finder")
    print("=" * 80)

    deals = run(
        query=args.query,
        threshold=args.threshold,
        min_price=args.min_price,
        max_price=args.max_price,
        sold_pages=args.sold_pages,
        listing_pages=args.listing_pages,
    )

    display_deals(deals)

    if deals:
        print(f"  TIP: Prices include shipping. Market price is based on recent eBay AU sales.")
        print(f"  Always verify the listing details before purchasing.\n")

    return 0 if deals else 1


if __name__ == "__main__":
    sys.exit(main())
