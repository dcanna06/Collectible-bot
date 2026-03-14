#!/usr/bin/env python3
"""Pokemon Card Price Bot – finds undervalued Pokemon card listings on eBay
Australia and Facebook Marketplace, and monitors auctions in real time.

Usage:
    python bot.py search                             # Search eBay + Facebook
    python bot.py search "Charizard VMAX"            # Specific card
    python bot.py search --source ebay               # eBay only
    python bot.py monitor                            # Monitor auctions (default query)
    python bot.py monitor "Charizard"                # Monitor specific card auctions
    python bot.py monitor --threshold 15 --interval 5
"""

import argparse
import sys

from tabulate import tabulate

import config
from scraper import fetch_sold_prices, fetch_active_listings
from facebook_scraper import fetch_facebook_listings
from analyzer import compute_market_prices, find_deals
from auction_monitor import run_monitor

VALID_SOURCES = ("all", "ebay", "facebook")


# ---------------------------------------------------------------------------
# search subcommand
# ---------------------------------------------------------------------------

def cmd_search(args):
    """Run the one-shot deal finder across eBay/Facebook."""
    config.DEFAULT_MIN_PRICE = args.min_price
    config.DEFAULT_MAX_PRICE = args.max_price

    search_ebay = args.source in ("all", "ebay")
    search_fb = args.source in ("all", "facebook")

    total_steps = 2 + int(search_ebay) + int(search_fb)
    step = 0

    # Step 1: Fetch sold prices
    step += 1
    print(f"\n[{step}/{total_steps}] Fetching recent sold prices for: \"{args.query}\" ...")
    sold = fetch_sold_prices(args.query, max_pages=args.sold_pages)
    print(f"      Found {len(sold)} sold listings.")

    if not sold:
        print("\n  No sold data found. Try a more specific search query.")
        return 1

    # Step 2: Compute market prices
    step += 1
    print(f"\n[{step}/{total_steps}] Computing market prices from sold data ...")
    market = compute_market_prices(sold)
    print(f"      Computed prices for {len(market)} unique card groupings.")

    # Step 3+: Fetch active listings
    all_active = []

    if search_ebay:
        step += 1
        print(f"\n[{step}/{total_steps}] Fetching active eBay AU listings for: \"{args.query}\" ...")
        ebay_active = fetch_active_listings(args.query, max_pages=args.listing_pages)
        print(f"      Found {len(ebay_active)} eBay listings.")
        all_active.extend(ebay_active)

    if search_fb:
        step += 1
        print(f"\n[{step}/{total_steps}] Fetching Facebook Marketplace listings for: \"{args.query}\" ...")
        fb_active = fetch_facebook_listings(
            args.query,
            locations=args.fb_locations,
            min_price=args.min_price,
            max_price=args.max_price,
        )
        print(f"      Found {len(fb_active)} Facebook Marketplace listings.")
        all_active.extend(fb_active)

    if not all_active:
        print("\n  No active listings found on any platform.")
        return 1

    print(f"\n  Analyzing {len(all_active)} total listings for deals "
          f"(>= {args.threshold}% below market) ...")
    deals = find_deals(all_active, market, threshold_percent=args.threshold)

    display_deals(deals)

    if deals:
        print(f"  TIP: eBay prices include shipping. FB Marketplace is typically local pickup.")
        print(f"  Market price is based on recent eBay AU sold data.")
        print(f"  Always verify the listing details before purchasing.\n")

    return 0 if deals else 1


# ---------------------------------------------------------------------------
# monitor subcommand
# ---------------------------------------------------------------------------

def cmd_monitor(args):
    """Run the real-time auction monitor with email alerts."""
    config.DEFAULT_MIN_PRICE = args.min_price
    config.DEFAULT_MAX_PRICE = args.max_price

    if args.email:
        config.ALERT_EMAIL_TO = args.email

    try:
        run_monitor(
            query=args.query,
            threshold=args.threshold,
            sold_pages=args.sold_pages,
            auction_pages=args.auction_pages,
            alert_window_minutes=args.alert_window,
            poll_interval_minutes=args.interval,
        )
    except KeyboardInterrupt:
        print("\n  Monitor stopped.")

    return 0


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Pokemon Card Price Bot – find undervalued cards on eBay AU "
            "and Facebook Marketplace, or monitor auctions in real time."
        )
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- search ---
    search_p = subparsers.add_parser(
        "search",
        help="One-shot search for undervalued Buy It Now listings.",
    )
    search_p.add_argument(
        "query", nargs="?", default=config.DEFAULT_SEARCH_QUERY,
        help=f"Search query (default: '{config.DEFAULT_SEARCH_QUERY}')",
    )
    search_p.add_argument(
        "--source", choices=VALID_SOURCES, default="all",
        help="Which marketplace(s) to search (default: all)",
    )
    search_p.add_argument(
        "--threshold", type=float, default=config.DEAL_THRESHOLD_PERCENT,
        help=f"Minimum discount %% (default: {config.DEAL_THRESHOLD_PERCENT}%%)",
    )
    search_p.add_argument(
        "--min-price", type=float, default=config.DEFAULT_MIN_PRICE,
        help=f"Minimum price in AUD (default: {config.DEFAULT_MIN_PRICE})",
    )
    search_p.add_argument(
        "--max-price", type=float, default=config.DEFAULT_MAX_PRICE,
        help=f"Maximum price in AUD (default: {config.DEFAULT_MAX_PRICE})",
    )
    search_p.add_argument(
        "--sold-pages", type=int, default=2,
        help="Pages of sold data to fetch (default: 2)",
    )
    search_p.add_argument(
        "--listing-pages", type=int, default=3,
        help="Pages of active listings to fetch (default: 3)",
    )
    search_p.add_argument(
        "--fb-locations", nargs="+", default=None,
        help="Facebook Marketplace locations to search",
    )

    # --- monitor ---
    monitor_p = subparsers.add_parser(
        "monitor",
        help="Monitor eBay auctions in real time and email alerts for deals.",
    )
    monitor_p.add_argument(
        "query", nargs="?", default=config.DEFAULT_SEARCH_QUERY,
        help=f"Search query (default: '{config.DEFAULT_SEARCH_QUERY}')",
    )
    monitor_p.add_argument(
        "--threshold", type=float, default=config.DEAL_THRESHOLD_PERCENT,
        help=f"Minimum discount %% to alert on (default: {config.DEAL_THRESHOLD_PERCENT}%%)",
    )
    monitor_p.add_argument(
        "--min-price", type=float, default=config.DEFAULT_MIN_PRICE,
        help=f"Minimum price in AUD (default: {config.DEFAULT_MIN_PRICE})",
    )
    monitor_p.add_argument(
        "--max-price", type=float, default=config.DEFAULT_MAX_PRICE,
        help=f"Maximum price in AUD (default: {config.DEFAULT_MAX_PRICE})",
    )
    monitor_p.add_argument(
        "--sold-pages", type=int, default=2,
        help="Pages of sold data to fetch (default: 2)",
    )
    monitor_p.add_argument(
        "--auction-pages", type=int, default=3,
        help="Pages of auctions to scan each cycle (default: 3)",
    )
    monitor_p.add_argument(
        "--alert-window", type=int, default=config.MONITOR_ALERT_WINDOW_MINUTES,
        help=f"Alert when auction ends within N minutes (default: {config.MONITOR_ALERT_WINDOW_MINUTES})",
    )
    monitor_p.add_argument(
        "--interval", type=int, default=config.MONITOR_POLL_INTERVAL_MINUTES,
        help=f"Minutes between scans (default: {config.MONITOR_POLL_INTERVAL_MINUTES})",
    )
    monitor_p.add_argument(
        "--email", type=str, default=None,
        help=f"Override alert email address (default: {config.ALERT_EMAIL_TO})",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 90)
    print("  POKEMON CARD PRICE BOT – eBay AU & Facebook Marketplace")
    print("=" * 90)

    if args.command == "search":
        source_desc = {
            "all": "eBay AU + Facebook Marketplace",
            "ebay": "eBay AU only",
            "facebook": "Facebook Marketplace only",
        }
        print(f"  Mode: Search | Sources: {source_desc[args.source]}")
        return cmd_search(args)

    elif args.command == "monitor":
        print(f"  Mode: Auction Monitor | Alerts to: {args.email or config.ALERT_EMAIL_TO}")
        return cmd_monitor(args)

    else:
        parser.print_help()
        print("\n  Use 'search' for one-shot deal finding or 'monitor' for real-time auction alerts.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
