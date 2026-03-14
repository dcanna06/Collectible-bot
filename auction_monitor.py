"""Real-time auction monitor.

Continuously scans eBay AU auctions for Pokemon cards. When an auction is
within ~1 hour of ending and the current bid is below the average sold price,
sends an email alert with the listing URL and previous sale prices.
"""

import time
from datetime import timedelta

import config
from scraper import fetch_sold_prices, fetch_auctions_ending_soon
from analyzer import normalize_title, compute_market_prices
from notifier import send_alert_email


def _build_sold_price_lookup(sold_listings):
    """Build a lookup of normalized title -> list of individual sold prices."""
    from collections import defaultdict
    groups = defaultdict(list)
    for listing in sold_listings:
        key = normalize_title(listing["title"])
        if key:
            groups[key].append(listing["total_price"])
    return groups


def run_monitor(query, threshold=None, sold_pages=2, auction_pages=3,
                alert_window_minutes=None, poll_interval_minutes=None):
    """Run the auction monitor loop.

    Args:
        query: Search query for Pokemon cards.
        threshold: Min discount % to trigger an alert (default from config).
        sold_pages: Pages of sold data to fetch for market prices.
        auction_pages: Pages of auctions to scan each cycle.
        alert_window_minutes: Alert on auctions ending within this many minutes.
        poll_interval_minutes: How often to re-scan (minutes).
    """
    if threshold is None:
        threshold = config.DEAL_THRESHOLD_PERCENT
    if alert_window_minutes is None:
        alert_window_minutes = config.MONITOR_ALERT_WINDOW_MINUTES
    if poll_interval_minutes is None:
        poll_interval_minutes = config.MONITOR_POLL_INTERVAL_MINUTES

    # Track which auctions we've already alerted on (by URL)
    alerted = set()

    print(f"\n{'=' * 70}")
    print(f"  AUCTION MONITOR – Real-Time eBay AU Deal Alerts")
    print(f"{'=' * 70}")
    print(f"  Query:          \"{query}\"")
    print(f"  Alert window:   Auctions ending within {alert_window_minutes} minutes")
    print(f"  Threshold:      {threshold}% below market value")
    print(f"  Poll interval:  Every {poll_interval_minutes} minutes")
    print(f"  Alerts sent to: {config.ALERT_EMAIL_TO}")
    print(f"{'=' * 70}")
    print(f"\n  Press Ctrl+C to stop.\n")

    cycle = 0

    while True:
        cycle += 1
        print(f"\n--- Cycle {cycle} ---")

        # Step 1: Refresh sold price data (market baseline)
        print(f"  Fetching sold prices for market data ...")
        sold = fetch_sold_prices(query, max_pages=sold_pages)
        if not sold:
            print(f"  No sold data found. Retrying in {poll_interval_minutes} min ...")
            time.sleep(poll_interval_minutes * 60)
            continue

        market = compute_market_prices(sold)
        sold_lookup = _build_sold_price_lookup(sold)
        print(f"  Market data: {len(market)} card groupings from {len(sold)} sales.")

        # Step 2: Fetch auctions ending soon
        # We search for auctions ending within a wider window (2h) to catch them
        # as they approach the alert window
        print(f"  Scanning auctions ending within {alert_window_minutes} min ...")
        auctions = fetch_auctions_ending_soon(
            query,
            max_pages=auction_pages,
            ending_within_hours=max(alert_window_minutes / 60 + 0.5, 2),
        )
        print(f"  Found {len(auctions)} auctions ending soon.")

        # Step 3: Check each auction against market prices
        alert_cutoff = timedelta(minutes=alert_window_minutes)
        alerts_sent = 0

        for auction in auctions:
            # Skip if already alerted
            if auction["url"] in alerted:
                continue

            # Only alert if within the alert window
            if auction["time_left"] > alert_cutoff:
                continue

            # Match against market data
            norm = normalize_title(auction["title"])
            if norm not in market:
                continue

            market_info = market[norm]
            if market_info["num_sales"] < 2:
                continue

            market_price = market_info["avg_price"]
            auction_price = auction["total_price"]

            if market_price <= 0:
                continue

            discount = ((market_price - auction_price) / market_price) * 100

            if discount < threshold:
                continue

            # This is a deal! Send alert.
            individual_prices = sold_lookup.get(norm, [])
            print(f"\n  DEAL FOUND: {auction['title'][:50]}")
            print(f"    Bid: ${auction_price:.2f} | Market: ${market_price:.2f} | "
                  f"Discount: {discount:.1f}% | Ends: {auction['time_left_str']}")

            success = send_alert_email(auction, market_info, individual_prices)
            if success:
                alerted.add(auction["url"])
                alerts_sent += 1

        if alerts_sent:
            print(f"\n  Sent {alerts_sent} alert(s) this cycle.")
        else:
            print(f"  No new deals to alert on.")

        print(f"  Sleeping {poll_interval_minutes} min until next scan ...")
        print(f"  (Tracking {len(alerted)} already-alerted auctions)")

        try:
            time.sleep(poll_interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n  Monitor stopped by user.")
            break
