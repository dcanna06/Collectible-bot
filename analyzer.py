"""Comparison engine: finds active listings priced below recent sold prices."""

import re
from collections import defaultdict

import config


def normalize_title(title):
    """Normalize a card title for grouping similar cards together.

    Strips common noise words and lowercases to group variants of the same card.
    """
    title = title.lower()
    # Remove common noise
    noise = [
        r"\bfree\s*post(age)?\b", r"\baus(tralia)?\b", r"\bau\b",
        r"\bnm\b", r"\bmint\b", r"\bnear\s*mint\b", r"\bpsa\b",
        r"\bcgc\b", r"\bbgs\b", r"\bgraded\b",
        r"\bholo\b", r"\bholographic\b", r"\breverse\b",
        r"\benglish\b", r"\bjapanese\b",
        r"\bpokemon\b", r"\btcg\b", r"\bcard\b",
        r"\bnew\b", r"\bsealed\b", r"\bused\b",
        r"[^\w\s/]",  # remove punctuation
    ]
    for pattern in noise:
        title = re.sub(pattern, " ", title)
    # Collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    return title


def compute_market_prices(sold_listings, sample_size=None):
    """Compute average sold price per normalized card name.

    Args:
        sold_listings: List of sold listing dicts from scraper.
        sample_size: Max recent sales to average per card (default from config).

    Returns:
        dict mapping normalized_title -> {
            'avg_price': float,
            'num_sales': int,
            'sample_titles': [str, ...],  # original titles for reference
        }
    """
    if sample_size is None:
        sample_size = config.SOLD_LISTINGS_SAMPLE_SIZE

    groups = defaultdict(list)
    for listing in sold_listings:
        key = normalize_title(listing["title"])
        if key:
            groups[key].append(listing)

    market = {}
    for key, listings in groups.items():
        # Take up to sample_size most recent (they come in recent-first order)
        sample = listings[:sample_size]
        prices = [l["total_price"] for l in sample]
        avg = sum(prices) / len(prices)
        market[key] = {
            "avg_price": round(avg, 2),
            "num_sales": len(sample),
            "sample_titles": [l["title"] for l in sample[:3]],
        }

    return market


def find_deals(active_listings, market_prices, threshold_percent=None):
    """Find active listings priced significantly below market value.

    Args:
        active_listings: List of active listing dicts from scraper.
        market_prices: Dict from compute_market_prices().
        threshold_percent: Minimum discount % to qualify as a deal.

    Returns:
        List of deal dicts sorted by discount (best deals first):
        [{
            'title': str,
            'listing_price': float,
            'market_price': float,
            'discount_percent': float,
            'savings': float,
            'url': str,
        }, ...]
    """
    if threshold_percent is None:
        threshold_percent = config.DEAL_THRESHOLD_PERCENT

    deals = []

    for listing in active_listings:
        norm = normalize_title(listing["title"])
        if norm not in market_prices:
            continue

        market_info = market_prices[norm]
        market_price = market_info["avg_price"]
        listing_price = listing["total_price"]

        # Skip if market data is thin (fewer than 2 sales)
        if market_info["num_sales"] < 2:
            continue

        if market_price <= 0:
            continue

        discount = ((market_price - listing_price) / market_price) * 100

        if discount >= threshold_percent:
            deals.append({
                "title": listing["title"],
                "listing_price": listing_price,
                "market_price": market_price,
                "discount_percent": round(discount, 1),
                "savings": round(market_price - listing_price, 2),
                "url": listing["url"],
                "num_sold_compared": market_info["num_sales"],
            })

    # Sort by biggest discount first
    deals.sort(key=lambda d: d["discount_percent"], reverse=True)
    return deals[:config.MAX_RESULTS_DISPLAY]
