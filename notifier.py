"""Email notification module for auction alerts."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import config


def send_alert_email(auction, market_info, sold_prices):
    """Send an email alert for an undervalued auction.

    Args:
        auction: Auction dict from scraper (title, current_bid, url, etc.).
        market_info: Dict with avg_price, num_sales from analyzer.
        sold_prices: List of individual sold price floats for context.
    """
    subject = f"Pokemon Card Deal Alert: {auction['title'][:60]}"

    current = auction["current_bid"]
    shipping = auction.get("shipping", 0)
    total = auction.get("total_price", current + shipping)
    market_avg = market_info["avg_price"]
    discount = ((market_avg - total) / market_avg) * 100

    # Build the sold price history lines
    sold_lines = ""
    for i, price in enumerate(sold_prices[:10], 1):
        sold_lines += f"    {i}. AU ${price:.2f}\n"

    time_left_str = auction.get("time_left_str", "unknown")
    bids = auction.get("bids", 0)

    body = f"""AUCTION DEAL ALERT
{'=' * 60}

Card:           {auction['title']}
Current Bid:    AU ${current:.2f}
Shipping:       AU ${shipping:.2f}
Total Price:    AU ${total:.2f}
Bids:           {bids}
Time Left:      {time_left_str}

MARKET COMPARISON
{'-' * 60}
Avg Sold Price: AU ${market_avg:.2f}
Discount:       {discount:.1f}% below market
Savings:        AU ${market_avg - total:.2f}
Based on:       {market_info['num_sales']} recent sales

RECENT SOLD PRICES
{'-' * 60}
{sold_lines}
LISTING URL
{'-' * 60}
{auction['url']}

{'=' * 60}
This alert was sent by Pokemon Card Price Bot.
Auction is ending soon — act fast!
"""

    html = f"""<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<div style="background: #dc3545; color: white; padding: 15px; border-radius: 8px 8px 0 0;">
    <h2 style="margin: 0;">Auction Deal Alert</h2>
</div>
<div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 8px 8px;">

<h3 style="color: #333;">{auction['title']}</h3>

<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
    <tr style="background: #f8f9fa;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Current Bid</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">AU ${current:.2f}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Shipping</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">AU ${shipping:.2f}</td>
    </tr>
    <tr style="background: #d4edda;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Price</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>AU ${total:.2f}</strong></td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Bids</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{bids}</td>
    </tr>
    <tr style="background: #fff3cd;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time Left</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>{time_left_str}</strong></td>
    </tr>
</table>

<h4 style="color: #333;">Market Comparison</h4>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
    <tr style="background: #f8f9fa;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Avg Sold Price</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">AU ${market_avg:.2f}</td>
    </tr>
    <tr style="background: #d4edda;">
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Discount</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd; color: #28a745; font-weight: bold;">
            {discount:.1f}% below market (save AU ${market_avg - total:.2f})
        </td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Based on</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{market_info['num_sales']} recent sales</td>
    </tr>
</table>

<h4 style="color: #333;">Recent Sold Prices</h4>
<ul style="margin: 10px 0;">
"""
    for price in sold_prices[:10]:
        html += f'    <li>AU ${price:.2f}</li>\n'

    html += f"""</ul>

<div style="text-align: center; margin: 20px 0;">
    <a href="{auction['url']}" style="background: #007bff; color: white; padding: 12px 30px;
       text-decoration: none; border-radius: 5px; font-size: 16px;">
       View Auction on eBay
    </a>
</div>

<p style="color: #666; font-size: 12px; margin-top: 20px;">
    This alert was sent by Pokemon Card Price Bot. Auction ending soon — act fast!
</p>
</div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.ALERT_EMAIL_TO

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if config.SMTP_USE_TLS:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT)

        if config.SMTP_USER and config.SMTP_PASSWORD:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)

        server.sendmail(config.EMAIL_FROM, [config.ALERT_EMAIL_TO], msg.as_string())
        server.quit()
        print(f"  [EMAIL] Alert sent to {config.ALERT_EMAIL_TO}: {auction['title'][:50]}")
        return True
    except Exception as e:
        print(f"  [!] Failed to send email: {e}")
        return False
