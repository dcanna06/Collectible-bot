"""Configuration for the Pokemon Card Price Bot."""

# eBay domain for Australia
EBAY_AU_BASE_URL = "https://www.ebay.com.au"

# Facebook Marketplace
FB_MARKETPLACE_BASE_URL = "https://www.facebook.com/marketplace"
FB_DEFAULT_LOCATION = "sydney"
FB_SEARCH_LOCATIONS = [
    "sydney",
    "melbourne",
    "brisbane",
    "perth",
    "adelaide",
    "hobart",
    "canberra",
    "darwin",
]
FB_REQUEST_DELAY = 2.0  # seconds between FB requests (be extra polite)

# Search parameters
DEFAULT_SEARCH_QUERY = "Pokemon card"
DEFAULT_MIN_PRICE = 1.0  # AUD - ignore junk listings
DEFAULT_MAX_PRICE = 5000.0  # AUD

# How far below market value (%) a listing must be to count as a deal
DEAL_THRESHOLD_PERCENT = 20  # 20% below market value

# Number of recent sold listings to average for fair price
SOLD_LISTINGS_SAMPLE_SIZE = 10

# Request settings
REQUEST_TIMEOUT = 15  # seconds
REQUEST_DELAY = 1.5  # seconds between requests to be polite
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Output settings
MAX_RESULTS_DISPLAY = 50
