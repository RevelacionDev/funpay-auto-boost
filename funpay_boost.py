"""
FunPay Auto-Boost Script  (Cloudflare-resistant)
=================================================
Clicks "Boost offers" on your FunPay lots every 4 hours.
Uses golden_key cookie auth + stealth patches to avoid Cloudflare detection.

HOW TO GET YOUR golden_key
───────────────────────────
Option A (DevTools):
  1. Open funpay.com in Chrome while logged in
  2. Press F12  →  Application tab  →  Cookies  →  funpay.com
  3. Find the row "golden_key" and copy its Value

Option B (extension, easier):
  1. Install "Cookie-Editor" extension in Chrome
  2. Go to funpay.com (logged in)  →  click the extension icon
  3. Find golden_key  →  copy its value

Paste that value into GOLDEN_KEY below. It lasts 100 days.

SETUP COMMANDS (run once in cmd):
  pip install playwright
  playwright install chromium
"""

import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Stealth JS injected directly — patches navigator.webdriver, chrome object,
# plugins, permissions API, and other signals Cloudflare fingerprints.
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

window.chrome = { runtime: {} };

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""

# ══════════════════════════════════════════════════════════════
#  ↓↓↓  ONLY EDIT THIS SECTION  ↓↓↓
# ══════════════════════════════════════════════════════════════

GOLDEN_KEY = "paste_your_golden_key_here"

OFFERS_PAGES = [
    "https://funpay.com/en/lots/[YOUR_LOT_ID_1]/trade",
    "https://funpay.com/en/lots/[YOUR_LOT_ID_2]/trade",
]

BOOST_EVERY_HOURS = 4
HEADLESS          = False  # Keep False unless you confirmed it works headless

# ══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("funpay_boost.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("FunPayBoost")


async def make_stealthy_page(context):
    """Create a page with Cloudflare-evasion patches applied."""
    page = await context.new_page()
    # Inject stealth patches before any page load
    await page.add_init_script(STEALTH_SCRIPT)
    return page


async def verify_auth(page) -> bool:
    log.info("Verifying golden_key authentication…")
    await page.goto("https://funpay.com/en/", wait_until="domcontentloaded")
    await asyncio.sleep(2)

    # If we hit a Cloudflare challenge page, warn clearly
    content = await page.content()
    if "cf-browser-verification" in content or "challenge-platform" in content:
        log.warning("Cloudflare challenge detected on homepage. Waiting 10s…")
        await asyncio.sleep(10)
        content = await page.content()
        if "cf-browser-verification" in content:
            return False  # Still blocked after waiting

    # Check for logged-in indicators
    logged_in = await page.locator(".user-link-name, .username, .header-nav-user").count()
    return logged_in > 0


async def boost_page(page, url: str) -> bool:
    log.info("Opening: %s", url)
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(2)

    # Handle any Cloudflare challenge that might appear mid-session
    content = await page.content()
    if "cf-browser-verification" in content or "Just a moment" in await page.title():
        log.warning("Cloudflare challenge on %s — waiting 15s for auto-solve…", url)
        await asyncio.sleep(15)  # CF's JS challenge usually auto-solves in ~5s

    # FunPay's Boost button carries class "js-lot-raise"
    btn = page.locator(".js-lot-raise").first

    try:
        await btn.wait_for(state="visible", timeout=12_000)
    except PlaywrightTimeout:
        log.warning("⚠ Boost button not found on %s", url)
        return False

    disabled = await btn.get_attribute("disabled")
    classes  = await btn.get_attribute("class") or ""
    if disabled is not None or "disabled" in classes:
        log.info("⏸ Cooldown not expired yet on %s", url)
        return False

    await btn.click()
    await asyncio.sleep(2)

    try:
        msg = await page.locator("#site-message").inner_text(timeout=3_000)
        if msg.strip():
            log.info("   FunPay says: %s", msg.strip())
    except Exception:
        pass

    log.info("✓ Boosted: %s", url)
    return True


async def main():
    if GOLDEN_KEY.startswith("paste_your"):
        print()
        print("  ⚠  GOLDEN_KEY is not set!")
        print("     Open funpay_boost.py in Notepad and paste your golden_key.")
        print()
        input("Press Enter to close…")
        return

    log.info("═" * 56)
    log.info("  FunPay Auto-Boost  │  Every %dh  │  %d lots",
             BOOST_EVERY_HOURS, len(OFFERS_PAGES))
    log.info("═" * 56)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=[
                # Core flag: tells Chrome not to announce it's automated
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                # A normal Windows Chrome user agent — not "HeadlessChrome"
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Europe/Moscow",
        )

        # Inject golden_key — skips the login form entirely
        await context.add_cookies([{
            "name":     "golden_key",
            "value":    GOLDEN_KEY,
            "domain":   "funpay.com",
            "path":     "/",
            "httpOnly": True,
            "secure":   True,
            "sameSite": "Lax",
        }])

        # Each page gets stealth patches on creation
        page = await make_stealthy_page(context)

        if not await verify_auth(page):
            log.error("✗ Auth failed — golden_key expired or Cloudflare blocked us.")
            log.error("  → Try running with HEADLESS=False to see what's happening.")
            await browser.close()
            input("Press Enter to close…")
            return

        log.info("✓ Authenticated. Starting boost loop.")

        cycle = 0
        while True:
            cycle += 1
            log.info("")
            log.info("── Cycle #%d ─────────────────────────────────────", cycle)

            for url in OFFERS_PAGES:
                try:
                    await boost_page(page, url)
                except Exception as e:
                    log.error("Error on %s: %s", url, e)

            log.info("")
            log.info("Sleeping %dh until next boost…", BOOST_EVERY_HOURS)
            await asyncio.sleep(BOOST_EVERY_HOURS * 3600)


if __name__ == "__main__":
    asyncio.run(main())
