"""eBay scraper for Pokemon card sold prices and active listings (Australia)."""

import re
import time
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
