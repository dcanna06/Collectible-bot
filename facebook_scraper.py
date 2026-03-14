"""Facebook Marketplace scraper for Pokemon card listings in Australia.

Facebook Marketplace does not provide an official API for listing search.
This module scrapes the public marketplace search endpoint, which returns
listings without requiring authentication for basic browsing.

Note: Facebook may rate-limit or block requests. Use responsibly.
"""

import re
import json
import time
from urllib.parse import quote_plus, urlencode

import requests
from bs4 import BeautifulSoup

import config


def _get_session():
    """Create a requests session with headers that mimic a browser."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })
    return session


def _parse_price(text):
    """Extract a numeric AUD price from text like 'A$25', '$25.00', etc."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def _build_marketplace_url(query, location=None, min_price=None, max_price=None):
    """Build a Facebook Marketplace search URL for Australia.

    Args:
        query: Search keywords.
        location: City/region slug (e.g. 'sydney', 'melbourne'). Uses config default.
        min_price: Minimum price filter (AUD).
        max_price: Maximum price filter (AUD).
    """
    if location is None:
        location = config.FB_DEFAULT_LOCATION

    base = f"{config.FB_MARKETPLACE_BASE_URL}/{location}/search"
    params = {
        "query": query,
        "exact": "false",
    }

    if min_price is not None:
        params["minPrice"] = str(int(min_price))
    if max_price is not None:
        params["maxPrice"] = str(int(max_price))

    return f"{base}?{urlencode(params)}"


def _extract_listings_from_html(html_text):
    """Extract listing data from Facebook Marketplace HTML.

    Facebook embeds listing data in JSON-LD and in structured data within
    the page. This tries multiple strategies to extract listings.
    """
    listings = []
    soup = BeautifulSoup(html_text, "lxml")

    # Strategy 1: Parse JSON-LD structured data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    listing = _parse_jsonld_item(item)
                    if listing:
                        listings.append(listing)
            elif isinstance(data, dict):
                if data.get("@type") == "ItemList":
                    for element in data.get("itemListElement", []):
                        item = element.get("item", element)
                        listing = _parse_jsonld_item(item)
                        if listing:
                            listings.append(listing)
                else:
                    listing = _parse_jsonld_item(data)
                    if listing:
                        listings.append(listing)
        except (json.JSONDecodeError, TypeError):
            continue

    # Strategy 2: Look for embedded relay-style JSON data in scripts
    if not listings:
        for script in soup.find_all("script"):
            if not script.string:
                continue
            listings.extend(_extract_from_relay_data(script.string))

    # Strategy 3: Parse HTML elements directly
    if not listings:
        listings.extend(_extract_from_html_elements(soup))

    return listings


def _parse_jsonld_item(item):
    """Parse a single JSON-LD product item into our listing format."""
    if not isinstance(item, dict):
        return None

    name = item.get("name", "")
    if not name:
        return None

    # Price can be in offers or directly
    price = None
    offers = item.get("offers", {})
    if isinstance(offers, dict):
        price_text = offers.get("price") or offers.get("lowPrice")
        if price_text:
            price = _parse_price(str(price_text))
    if price is None:
        price = _parse_price(str(item.get("price", "")))

    if price is None:
        return None

    url = item.get("url", "")
    if url and not url.startswith("http"):
        url = f"https://www.facebook.com{url}"

    location = ""
    avail_at = item.get("availableAtOrFrom", {})
    if isinstance(avail_at, dict):
        addr = avail_at.get("address", {})
        if isinstance(addr, dict):
            location = addr.get("addressLocality", "")

    return {
        "title": name,
        "price": price,
        "shipping": 0.0,  # Marketplace is typically local pickup
        "total_price": price,
        "url": url,
        "location": location,
        "source": "facebook",
    }


def _extract_from_relay_data(script_text):
    """Try to find marketplace listing data embedded in Facebook's relay JSON."""
    listings = []

    # Look for patterns like "marketplace_search" or "edge" with listing nodes
    patterns = [
        r'"marketplace_listing_title"\s*:\s*"([^"]+)"',
    ]

    titles = []
    for pat in patterns:
        titles.extend(re.findall(pat, script_text))

    # Try to find price patterns near titles
    price_matches = re.findall(
        r'"listing_price"\s*:\s*\{[^}]*"amount"\s*:\s*"?([\d.]+)"?', script_text
    )

    # Try to find listing URLs
    url_matches = re.findall(
        r'"marketplace/item/(\d+)"', script_text
    )

    # Zip together what we found
    for i, title in enumerate(titles):
        price = None
        if i < len(price_matches):
            price = _parse_price(price_matches[i])
        if price is None:
            continue

        url = ""
        if i < len(url_matches):
            url = f"https://www.facebook.com/marketplace/item/{url_matches[i]}"

        # Unescape unicode
        title = title.encode().decode("unicode_escape", errors="replace")

        listings.append({
            "title": title,
            "price": price,
            "shipping": 0.0,
            "total_price": price,
            "url": url,
            "location": "",
            "source": "facebook",
        })

    return listings


def _extract_from_html_elements(soup):
    """Fallback: extract listings from HTML structure."""
    listings = []

    # Facebook Marketplace uses various div structures
    # Look for common patterns in listing cards
    for link in soup.find_all("a", href=re.compile(r"/marketplace/item/\d+")):
        title = ""
        price = None

        # The listing card typically has the title and price nearby
        card = link.find_parent("div", recursive=True)
        if not card:
            card = link

        # Look for text content that looks like a title
        spans = card.find_all("span")
        for span in spans:
            text = span.get_text(strip=True)
            if not text:
                continue
            # Price detection
            if re.match(r"^[A$\$]", text) and price is None:
                price = _parse_price(text)
            elif len(text) > 5 and not title:
                title = text

        if not title or price is None:
            continue

        href = link.get("href", "")
        if not href.startswith("http"):
            href = f"https://www.facebook.com{href}"
        # Strip tracking params
        if "?" in href:
            href = href.split("?")[0]

        listings.append({
            "title": title,
            "price": price,
            "shipping": 0.0,
            "total_price": price,
            "url": href,
            "location": "",
            "source": "facebook",
        })

    return listings


def fetch_facebook_listings(query, locations=None, min_price=None, max_price=None):
    """Fetch Facebook Marketplace listings for Pokemon cards in Australia.

    Args:
        query: Search query string.
        locations: List of city/region slugs to search. Defaults to config list.
        min_price: Minimum price in AUD.
        max_price: Maximum price in AUD.

    Returns:
        List of listing dicts: [{title, price, shipping, total_price, url,
                                  location, source}, ...]
    """
    if locations is None:
        locations = config.FB_SEARCH_LOCATIONS
    if min_price is None:
        min_price = config.DEFAULT_MIN_PRICE
    if max_price is None:
        max_price = config.DEFAULT_MAX_PRICE

    session = _get_session()
    all_listings = []
    seen_urls = set()

    for location in locations:
        url = _build_marketplace_url(
            query, location=location,
            min_price=min_price, max_price=max_price,
        )

        print(f"      Searching Facebook Marketplace: {location} ...")

        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [!] Error fetching FB Marketplace ({location}): {e}")
            continue

        listings = _extract_listings_from_html(resp.text)

        for listing in listings:
            if listing["url"] and listing["url"] not in seen_urls:
                if not listing["location"]:
                    listing["location"] = location.replace("-", " ").title()
                seen_urls.add(listing["url"])
                all_listings.append(listing)

        time.sleep(config.FB_REQUEST_DELAY)

    return all_listings
