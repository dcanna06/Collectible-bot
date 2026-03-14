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

# ---------------------------------------------------------------------------
# Email alert settings (for auction monitor)
# ---------------------------------------------------------------------------
ALERT_EMAIL_TO = "davecannalonga@gmail.com"
EMAIL_FROM = "pokemonbot.alerts@gmail.com"  # Sender address (configure with your SMTP)

# SMTP settings — configure these for your email provider
# Gmail example: host=smtp.gmail.com, port=587, use_tls=True
# You'll need an App Password if using Gmail with 2FA:
#   https://support.google.com/accounts/answer/185833
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USE_TLS = True
SMTP_USER = "pokemonbot.alerts@gmail.com"  # Your sending email
SMTP_PASSWORD = ""  # Set via SMTP_PASSWORD env var or paste here (NOT recommended)

# ---------------------------------------------------------------------------
# Auction monitor settings
# ---------------------------------------------------------------------------
# Alert on auctions ending within this many minutes
MONITOR_ALERT_WINDOW_MINUTES = 60  # 1 hour before auction ends

# How often the monitor re-scans for new auctions (minutes)
MONITOR_POLL_INTERVAL_MINUTES = 10


# ---------------------------------------------------------------------------
# Load sensitive settings from environment variables (preferred over hardcoding)
# ---------------------------------------------------------------------------
import os as _os

SMTP_PASSWORD = _os.environ.get("SMTP_PASSWORD", SMTP_PASSWORD)
SMTP_USER = _os.environ.get("SMTP_USER", SMTP_USER)
EMAIL_FROM = _os.environ.get("EMAIL_FROM", EMAIL_FROM)
ALERT_EMAIL_TO = _os.environ.get("ALERT_EMAIL_TO", ALERT_EMAIL_TO)
