"""eBay scraper for Pokemon card sold prices, active listings, and auctions (Australia)."""

import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urlencode

import requests
from bs4 import BeautifulSoup

import config


def _get_session():
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def _parse_price(text):
    """Extract a numeric AUD price from a string like 'AU $12.50'."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _build_search_url(query, sold=False, page=1, min_price=None, max_price=None):
    """Build an eBay AU search URL.

    Args:
        query: Search keywords.
        sold: If True, search completed/sold listings.
        page: Page number.
        min_price: Minimum price filter (AUD).
        max_price: Maximum price filter (AUD).
    """
    params = {
        "_nkw": query,
        "_sacat": "0",
        "_ipg": "60",  # results per page
    }

    if sold:
        # LH_Sold=1 and LH_Complete=1 filter to sold/completed items
        params["LH_Sold"] = "1"
        params["LH_Complete"] = "1"
        params["_sop"] = "13"  # sort by end date: recent first

    if min_price is not None:
        params["_udlo"] = str(min_price)
    if max_price is not None:
        params["_udhi"] = str(max_price)

    if page > 1:
        params["_pgn"] = str(page)

    return f"{config.EBAY_AU_BASE_URL}/sch/i.html?{urlencode(params)}"


def _parse_listing(item):
    """Parse a single listing item from eBay search results.

    Returns a dict with title, price, url, and shipping or None if unparseable.
    """
    # Title
    title_tag = item.select_one("div.s-item__title span[role='heading']")
    if not title_tag:
        title_tag = item.select_one("div.s-item__title")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)
    if title.lower() in ("shop on ebay", ""):
        return None

    # URL
    link_tag = item.select_one("a.s-item__link")
    url = link_tag["href"] if link_tag else None

    # Price
    price_tag = item.select_one("span.s-item__price")
    price_text = price_tag.get_text(strip=True) if price_tag else None

    # Handle price ranges like "AU $5.00 to AU $10.00" – take the lower bound
    if price_text and "to" in price_text.lower():
        price_text = price_text.split("to")[0].strip()

    price = _parse_price(price_text)

    # Shipping
    shipping_tag = item.select_one("span.s-item__shipping, span.s-item__freeXDays")
    shipping_text = ""
    if shipping_tag:
        shipping_text = shipping_tag.get_text(strip=True)
    shipping_cost = 0.0
    if "free" in shipping_text.lower():
        shipping_cost = 0.0
    else:
        parsed_shipping = _parse_price(shipping_text)
        if parsed_shipping is not None:
            shipping_cost = parsed_shipping

    if price is None:
        return None

    return {
        "title": title,
        "price": price,
        "shipping": shipping_cost,
        "total_price": round(price + shipping_cost, 2),
        "url": url,
        "source": "ebay",
    }


def fetch_sold_prices(query, max_pages=2):
    """Fetch recently sold prices for a given search query on eBay AU.

    Returns a list of dicts: [{title, price, shipping, total_price, url}, ...]
    sorted by most recent first.
    """
    session = _get_session()
    results = []

    for page in range(1, max_pages + 1):
        url = _build_search_url(
            query,
            sold=True,
            page=page,
            min_price=config.DEFAULT_MIN_PRICE,
            max_price=config.DEFAULT_MAX_PRICE,
        )
        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [!] Error fetching sold page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("li.s-item")

        for item in items:
            parsed = _parse_listing(item)
            if parsed:
                results.append(parsed)

        time.sleep(config.REQUEST_DELAY)

    return results


def fetch_active_listings(query, max_pages=3):
    """Fetch current active (Buy It Now) listings for a query on eBay AU.

    Returns a list of dicts: [{title, price, shipping, total_price, url}, ...]
    sorted by price (lowest first).
    """
    session = _get_session()
    results = []

    for page in range(1, max_pages + 1):
        params_extra = {
            "LH_BIN": "1",        # Buy It Now only
            "LH_ItemCondition": "",  # all conditions
            "_sop": "15",          # sort: Price + Shipping: lowest first
            "LH_PrefLoc": "1",     # items located in Australia
        }
        url = _build_search_url(
            query,
            sold=False,
            page=page,
            min_price=config.DEFAULT_MIN_PRICE,
            max_price=config.DEFAULT_MAX_PRICE,
        )
        # Append extra params
        extra = urlencode(params_extra)
        url = f"{url}&{extra}"

        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [!] Error fetching listings page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("li.s-item")

        for item in items:
            parsed = _parse_listing(item)
            if parsed:
                results.append(parsed)

        time.sleep(config.REQUEST_DELAY)

    return results


# ---------------------------------------------------------------------------
# Auction-specific scraping
# ---------------------------------------------------------------------------

def _parse_time_left(text):
    """Parse eBay time-left strings like '1h 23m', '3d 5h', '45m 12s'.

    Returns a timedelta or None if unparseable.
    """
    if not text:
        return None
    text = text.lower().strip()

    days = hours = minutes = seconds = 0
    for match in re.finditer(r"(\d+)\s*([dhms])", text):
        val = int(match.group(1))
        unit = match.group(2)
        if unit == "d":
            days = val
        elif unit == "h":
            hours = val
        elif unit == "m":
            minutes = val
        elif unit == "s":
            seconds = val

    td = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return td if td.total_seconds() > 0 else None


def _parse_auction_item(item):
    """Parse a single auction listing from eBay search results.

    Returns a dict with title, current_bid, time_left, end_time, url, bids
    or None if unparseable / not an auction.
    """
    # Title
    title_tag = item.select_one("div.s-item__title span[role='heading']")
    if not title_tag:
        title_tag = item.select_one("div.s-item__title")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)
    if title.lower() in ("shop on ebay", ""):
        return None

    # URL
    link_tag = item.select_one("a.s-item__link")
    url = link_tag["href"] if link_tag else None

    # Current bid price
    price_tag = item.select_one("span.s-item__price")
    price_text = price_tag.get_text(strip=True) if price_tag else None
    if price_text and "to" in price_text.lower():
        price_text = price_text.split("to")[0].strip()
    current_bid = _parse_price(price_text)
    if current_bid is None:
        return None

    # Time left
    time_tag = item.select_one("span.s-item__time-left")
    time_text = time_tag.get_text(strip=True) if time_tag else ""
    time_left = _parse_time_left(time_text)

    # Also check the end date element
    if time_left is None:
        end_tag = item.select_one("span.s-item__time-end")
        if end_tag:
            end_text = end_tag.get_text(strip=True)
            time_left = _parse_time_left(end_text)

    # If we still don't have time left, try the dynamic timer attribute
    if time_left is None:
        timer_tag = item.select_one("[data-timeleft]")
        if timer_tag:
            time_left = _parse_time_left(timer_tag.get("data-timeleft", ""))

    if time_left is None:
        return None

    now = datetime.now(timezone.utc)
    end_time = now + time_left

    # Number of bids
    bids_tag = item.select_one("span.s-item__bids")
    bids_text = bids_tag.get_text(strip=True) if bids_tag else "0"
    bids = 0
    bids_match = re.search(r"(\d+)", bids_text)
    if bids_match:
        bids = int(bids_match.group(1))

    # Shipping
    shipping_tag = item.select_one("span.s-item__shipping, span.s-item__freeXDays")
    shipping_text = shipping_tag.get_text(strip=True) if shipping_tag else ""
    shipping_cost = 0.0
    if "free" in shipping_text.lower():
        shipping_cost = 0.0
    else:
        parsed_shipping = _parse_price(shipping_text)
        if parsed_shipping is not None:
            shipping_cost = parsed_shipping

    return {
        "title": title,
        "current_bid": current_bid,
        "shipping": shipping_cost,
        "total_price": round(current_bid + shipping_cost, 2),
        "url": url,
        "bids": bids,
        "time_left": time_left,
        "time_left_str": time_text or str(time_left),
        "end_time": end_time,
        "source": "ebay_auction",
    }


def fetch_auctions_ending_soon(query, max_pages=3, ending_within_hours=2):
    """Fetch eBay AU auctions ending soon for a given query.

    Args:
        query: Search keywords.
        max_pages: Number of search result pages to scan.
        ending_within_hours: Only return auctions ending within this many hours.

    Returns:
        List of auction dicts sorted by end time (soonest first).
    """
    session = _get_session()
    results = []

    for page in range(1, max_pages + 1):
        params = {
            "_nkw": query,
            "_sacat": "0",
            "_ipg": "60",
            "LH_Auction": "1",      # Auctions only
            "_sop": "1",            # Sort: Time: ending soonest
            "LH_PrefLoc": "1",      # Located in Australia
        }
        if config.DEFAULT_MIN_PRICE:
            params["_udlo"] = str(config.DEFAULT_MIN_PRICE)
        if config.DEFAULT_MAX_PRICE:
            params["_udhi"] = str(config.DEFAULT_MAX_PRICE)
        if page > 1:
            params["_pgn"] = str(page)

        url = f"{config.EBAY_AU_BASE_URL}/sch/i.html?{urlencode(params)}"

        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [!] Error fetching auction page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("li.s-item")

        cutoff = timedelta(hours=ending_within_hours)
        found_past_cutoff = False

        for item in items:
            parsed = _parse_auction_item(item)
            if not parsed:
                continue
            if parsed["time_left"] <= cutoff:
                results.append(parsed)
            else:
                # Since sorted by ending soonest, once we pass cutoff we can stop
                found_past_cutoff = True
                break

        if found_past_cutoff:
            break

        time.sleep(config.REQUEST_DELAY)

    # Sort by end time ascending (soonest first)
    results.sort(key=lambda a: a["end_time"])
    return results


def fetch_single_auction(url):
    """Fetch current details for a single auction listing page.

    Returns a dict with current_bid, time_left, bids, end_time or None on error.
    """
    session = _get_session()
    try:
        resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [!] Error fetching auction page: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # Current bid from item page
    bid_tag = (
        soup.select_one("span.x-bid-count span.ux-textspans") or
        soup.select_one("#prcIsum") or
        soup.select_one("span[itemprop='price']") or
        soup.select_one("div.x-price-primary span.ux-textspans")
    )
    current_bid = None
    if bid_tag:
        current_bid = _parse_price(bid_tag.get_text(strip=True))

    # Time left from item page
    time_tag = (
        soup.select_one("span.ux-timer__text") or
        soup.select_one("span.vi-tm-left") or
        soup.select_one("div.x-timer span")
    )
    time_left = None
    if time_tag:
        time_left = _parse_time_left(time_tag.get_text(strip=True))

    # Bid count
    bids = 0
    bids_tag = soup.select_one("a[data-testid='x-bid-count'] span")
    if not bids_tag:
        bids_tag = soup.select_one("span.vi-qtyS-hot-red") or soup.select_one("a.vi-VR-bidCnt")
    if bids_tag:
        m = re.search(r"(\d+)", bids_tag.get_text(strip=True))
        if m:
            bids = int(m.group(1))

    if current_bid is None:
        return None

    now = datetime.now(timezone.utc)
    end_time = now + time_left if time_left else None

    return {
        "current_bid": current_bid,
        "time_left": time_left,
        "end_time": end_time,
        "bids": bids,
    }
