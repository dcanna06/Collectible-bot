#!/usr/bin/env python3
"""Pokemon Card Price Bot – finds undervalued Pokemon card listings on eBay
Australia and Facebook Marketplace.

Usage:
    python bot.py                                # Search eBay + Facebook
    python bot.py "Charizard VMAX"               # Search for a specific card
    python bot.py --source ebay                  # eBay only
    python bot.py --source facebook              # Facebook Marketplace only
    python bot.py --threshold 30                 # Only show 30%+ below market
    python bot.py --min-price 5 --max-price 200  # Price range filter
"""

import argparse
import sys

from tabulate import tabulate

import config
from scraper import fetch_sold_prices, fetch_active_listings
from facebook_scraper import fetch_facebook_listings
from analyzer import compute_market_prices, find_deals

VALID_SOURCES = ("all", "ebay", "facebook")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Find Pokemon cards listed below market value on "
            "eBay Australia and Facebook Marketplace."
        )
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=config.DEFAULT_SEARCH_QUERY,
        help=f"Search query (default: '{config.DEFAULT_SEARCH_QUERY}')",
    )
    parser.add_argument(
        "--source",
        choices=VALID_SOURCES,
        default="all",
        help="Which marketplace(s) to search: all, ebay, or facebook (default: all)",
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
        help="Number of eBay sold listing pages to fetch (default: 2)",
    )
    parser.add_argument(
        "--listing-pages",
        type=int,
        default=3,
        help="Number of eBay active listing pages to fetch (default: 3)",
    )
    parser.add_argument(
        "--fb-locations",
        nargs="+",
        default=None,
        help=(
            "Facebook Marketplace locations to search "
            f"(default: {', '.join(config.FB_SEARCH_LOCATIONS)})"
        ),
    )
    return parser.parse_args()


def run(query, source, threshold, min_price, max_price,
        sold_pages, listing_pages, fb_locations):
    """Run the full pipeline: scrape, analyze, and return deals."""

    # Temporarily override config prices
    config.DEFAULT_MIN_PRICE = min_price
    config.DEFAULT_MAX_PRICE = max_price

    search_ebay = source in ("all", "ebay")
    search_fb = source in ("all", "facebook")

    total_steps = 2 + int(search_ebay) + int(search_fb)
    step = 0

    # Step 1: Fetch sold prices (always needed for market value baseline)
    step += 1
    print(f"\n[{step}/{total_steps}] Fetching recent sold prices for: \"{query}\" ...")
    sold = fetch_sold_prices(query, max_pages=sold_pages)
    print(f"      Found {len(sold)} sold listings.")

    if not sold:
        print("\n  No sold data found. Try a more specific search query.")
        return []

    # Step 2: Compute market prices
    step += 1
    print(f"\n[{step}/{total_steps}] Computing market prices from sold data ...")
    market = compute_market_prices(sold)
    print(f"      Computed prices for {len(market)} unique card groupings.")

    # Step 3+: Fetch active listings from selected sources
    all_active = []

    if search_ebay:
        step += 1
        print(f"\n[{step}/{total_steps}] Fetching active eBay AU listings for: \"{query}\" ...")
        ebay_active = fetch_active_listings(query, max_pages=listing_pages)
        print(f"      Found {len(ebay_active)} eBay listings.")
        all_active.extend(ebay_active)

    if search_fb:
        step += 1
        print(f"\n[{step}/{total_steps}] Fetching Facebook Marketplace listings for: \"{query}\" ...")
        fb_active = fetch_facebook_listings(
            query,
            locations=fb_locations,
            min_price=min_price,
            max_price=max_price,
        )
        print(f"      Found {len(fb_active)} Facebook Marketplace listings.")
        all_active.extend(fb_active)

    if not all_active:
        print("\n  No active listings found on any platform.")
        return []

    # Final: Find deals
    print(f"\n  Analyzing {len(all_active)} total listings for deals "
          f"(>= {threshold}% below market) ...")
    deals = find_deals(all_active, market, threshold_percent=threshold)

    return deals


def display_deals(deals):
    """Print deals in a formatted table."""
    if not deals:
        print("\n  No deals found matching your criteria.")
        print("  Try broadening your search or lowering the discount threshold.")
        return

    print(f"\n{'=' * 90}")
    print(f"  DEALS FOUND: {len(deals)} listings below market value")
    print(f"{'=' * 90}\n")

    table_data = []
    for i, deal in enumerate(deals, 1):
        title = deal["title"]
        if len(title) > 45:
            title = title[:42] + "..."

        source_label = deal.get("source", "ebay").upper()
        if source_label == "FACEBOOK":
            source_label = "FB"

        table_data.append([
            i,
            source_label,
            title,
            f"${deal['listing_price']:.2f}",
            f"${deal['market_price']:.2f}",
            f"-{deal['discount_percent']}%",
            f"${deal['savings']:.2f}",
        ])

    headers = ["#", "Source", "Card", "Price", "Market", "Discount", "Savings"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Print URLs grouped by source
    print(f"\n{'─' * 90}")
    print("  LINKS:\n")

    ebay_deals = [d for d in deals if d.get("source") == "ebay"]
    fb_deals = [d for d in deals if d.get("source") == "facebook"]

    idx = 1
    if ebay_deals:
        print("  eBay Australia:")
        for deal in ebay_deals:
            print(f"    {idx}. {deal['url']}")
            idx += 1

    if fb_deals:
        if ebay_deals:
            print()
        print("  Facebook Marketplace:")
        for deal in fb_deals:
            loc = deal.get("location", "")
            suffix = f"  ({loc})" if loc else ""
            print(f"    {idx}. {deal['url']}{suffix}")
            idx += 1

    print()


def main():
    args = parse_args()

    print("=" * 90)
    print("  POKEMON CARD PRICE BOT – eBay AU & Facebook Marketplace Deal Finder")
    print("=" * 90)

    source_desc = {
        "all": "eBay AU + Facebook Marketplace",
        "ebay": "eBay AU only",
        "facebook": "Facebook Marketplace only",
    }
    print(f"  Searching: {source_desc[args.source]}")

    deals = run(
        query=args.query,
        source=args.source,
        threshold=args.threshold,
        min_price=args.min_price,
        max_price=args.max_price,
        sold_pages=args.sold_pages,
        listing_pages=args.listing_pages,
        fb_locations=args.fb_locations,
    )

    display_deals(deals)

    if deals:
        print(f"  TIP: eBay prices include shipping. FB Marketplace is typically local pickup.")
        print(f"  Market price is based on recent eBay AU sold data.")
        print(f"  Always verify the listing details before purchasing.\n")

    return 0 if deals else 1


if __name__ == "__main__":
    sys.exit(main())
