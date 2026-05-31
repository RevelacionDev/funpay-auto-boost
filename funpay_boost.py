"""
FunPay Auto-Boost v2.0  (Cloudflare-resistant)
===============================================
Features:
  - Auto-detects all offer categories from your profile page
  - Independent per-offer timing (handles manual boosts correctly)
  - Optional Telegram notifications
  - Daily log rotation

HOW TO GET YOUR golden_key:
  1. Open funpay.com in Chrome/Edge while logged in
  2. Press F12 → Application → Cookies → funpay.com
  3. Copy the Value of "golden_key"

HOW TO GET YOUR user ID:
  Open funpay.com → click your avatar → your profile URL is
  funpay.com/en/users/XXXXX/ — the number is your ID

SETUP (run once in PowerShell):
  pip install playwright
  python -m playwright install chromium

OPTIONAL TELEGRAM SETUP:
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Message @userinfobot on Telegram → copy your chat ID
  3. Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID below
"""

import asyncio
import json
import logging
import logging.handlers
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ══════════════════════════════════════════════════════════════
#  ↓↓↓  CONFIGURATION — only edit this section  ↓↓↓
# ══════════════════════════════════════════════════════════════

GOLDEN_KEY     = "paste_your_golden_key_here"
FUNPAY_USER_ID = "00000"   # numbers from funpay.com/en/users/XXXXX/

# How often to check if any offer is due for a boost (minutes)
# Script checks independently per offer — no waiting for others
CHECK_INTERVAL_MINUTES = 15

BOOST_COOLDOWN_HOURS = 4   # FunPay's cooldown — don't go lower

# Telegram — leave both empty to disable entirely
TELEGRAM_BOT_TOKEN = ""    # "123456789:ABCdef..."
TELEGRAM_CHAT_ID   = ""    # "123456789"

HEADLESS = True    # True = fully hidden, False = see the browser

# ══════════════════════════════════════════════════════════════

STATE_FILE = "boost_state.json"
LOG_FILE   = "funpay_boost.log"

# ── Logging: daily rotation, keep 3 days ─────────────────────
log = logging.getLogger("FunPayBoost")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%Y-%m-%d %H:%M:%S")

_fh = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE, when="midnight", backupCount=3, encoding="utf-8"
)
_fh.setFormatter(_fmt)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_ch)

# ── Stealth patches ───────────────────────────────────────────
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
const _origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (p) =>
    p.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : _origQuery(p);
"""

async def new_page(context):
    page = await context.new_page()
    await page.add_init_script(STEALTH_JS)
    return page

# ── State: tracks last confirmed boost time per offer URL ─────
def load_state() -> dict:
    try:
        if Path(STATE_FILE).exists():
            return json.loads(Path(STATE_FILE).read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_state(state: dict):
    Path(STATE_FILE).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def record_boost(state: dict, url: str, name: str):
    state[url] = {"name": name, "last_boost": datetime.now().isoformat()}
    save_state(state)

def is_due(state: dict, url: str) -> bool:
    entry = state.get(url)
    if not entry or not entry.get("last_boost"):
        return True
    last = datetime.fromisoformat(entry["last_boost"])
    return datetime.now() - last >= timedelta(hours=BOOST_COOLDOWN_HOURS)

def time_remaining(state: dict, url: str) -> str:
    entry = state.get(url)
    if not entry or not entry.get("last_boost"):
        return "unknown"
    last  = datetime.fromisoformat(entry["last_boost"])
    delta = timedelta(hours=BOOST_COOLDOWN_HOURS) - (datetime.now() - last)
    total = max(0, int(delta.total_seconds()))
    h, m  = divmod(total // 60, 60)
    return f"{h}h {m}m" if h else f"{m}m"

# ── Telegram ──────────────────────────────────────────────────
async def tg(msg: str):
    """Send a Telegram message. Silently logs to CLI only if Telegram is not configured."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import urllib.request, urllib.parse
    try:
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text":    msg,
            "parse_mode": "HTML",
        }).encode()
        urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data=data,
            ),
            timeout=10,
        )
        log.info("Telegram notification sent.")
    except Exception as e:
        log.warning("Telegram failed (CLI only): %s", e)

# ── Discover offer category URLs from profile page ────────────
async def discover_offers(page, state: dict) -> list[dict]:
    """
    Opens the user's profile page, finds every offer category's
    pencil/edit icon, and returns a list of {url, name} dicts.
    """
    profile = f"https://funpay.com/en/users/{FUNPAY_USER_ID}/"
    log.info("Scanning profile for offers: %s", profile)
    await page.goto(profile, wait_until="domcontentloaded")
    await asyncio.sleep(2)

    offers = []
    seen   = set()

    # Each offer category section has a pencil icon linking to /lots/ID/trade
    # We grab the link AND the nearest heading text as the category name
    sections = await page.locator("h3, h2").all()
    for section in sections:
        # Look for an <a href*="/lots/"> sibling or child within the same row
        container = section.locator("xpath=..").first  # parent element
        links = await container.locator('a[href*="/lots/"][href*="/trade"]').all()
        heading_text = (await section.inner_text()).strip().split("\n")[0].strip()

        for link in links:
            href = await link.get_attribute("href")
            if not href:
                continue
            url = href if href.startswith("http") else f"https://funpay.com{href}"
            # Normalise — strip trailing slash variants
            url = url.rstrip("/")
            if url in seen:
                continue
            seen.add(url)
            # Use existing name from state if we already know it
            name = state.get(url, {}).get("name") or heading_text or url
            offers.append({"url": url, "name": name})
            log.info("  Found: [%s] → %s", name, url)

    # Fallback: brute-force scan all matching anchors on the page
    if not offers:
        log.info("Section scan found nothing — trying full-page anchor scan…")
        links = await page.locator('a[href*="/lots/"][href*="/trade"]').all()
        for link in links:
            href = await link.get_attribute("href")
            if not href:
                continue
            url = (href if href.startswith("http") else f"https://funpay.com{href}").rstrip("/")
            if url in seen:
                continue
            seen.add(url)
            name = state.get(url, {}).get("name") or url
            offers.append({"url": url, "name": name})
            log.info("  Found (fallback): %s", url)

    return offers

# ── Boost a single offer page ─────────────────────────────────
async def boost_page(page, url: str, name: str) -> bool:
    """Returns True if the button was clicked successfully."""
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(2)

    btn = page.locator(".js-lot-raise").first
    try:
        await btn.wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeout:
        log.warning("Boost button not found on [%s] — skipping.", name)
        return False

    disabled = await btn.get_attribute("disabled")
    classes  = await btn.get_attribute("class") or ""
    if disabled is not None or "disabled" in classes:
        log.info("⏸ Button disabled on [%s] — manually boosted recently?", name)
        return False

    await btn.click()
    await asyncio.sleep(2)

    try:
        site_msg = await page.locator("#site-message").inner_text(timeout=3_000)
        if site_msg.strip():
            log.info("  FunPay says: %s", site_msg.strip())
    except Exception:
        pass

    log.info("✓ Boosted: [%s]", name)
    return True

# ── Main loop ─────────────────────────────────────────────────
async def main():
    if GOLDEN_KEY.startswith("paste_your"):
        print("\n  ⚠  Set your GOLDEN_KEY in the script first!\n")
        input("Press Enter to close…")
        return

    if FUNPAY_USER_ID == "00000":
        print("\n  ⚠  Set your FUNPAY_USER_ID in the script first!\n")
        print("  Open funpay.com → your avatar → check the URL for your ID number.\n")
        input("Press Enter to close…")
        return

    log.info("═" * 58)
    log.info("  FunPay Auto-Boost v2.0  │  Check every %dm", CHECK_INTERVAL_MINUTES)
    log.info("  Telegram: %s", "enabled ✓" if TELEGRAM_BOT_TOKEN else "disabled")
    log.info("═" * 58)

    state = load_state()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        await context.add_cookies([{
            "name": "golden_key", "value": GOLDEN_KEY,
            "domain": "funpay.com", "path": "/",
            "httpOnly": True, "secure": True, "sameSite": "Lax",
        }])

        page = await new_page(context)

        # Verify auth
        await page.goto("https://funpay.com/en/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        if not await page.locator(".user-link-name, .username, .header-nav-user").count():
            log.error("✗ golden_key invalid or expired. Get a fresh one from your browser.")
            await browser.close()
            input("Press Enter to close…")
            return

        log.info("✓ Authenticated.")
        await tg("🚀 <b>FunPay Auto-Boost v2.0 started</b>")

        # Initial offer discovery
        offers = await discover_offers(page, state)
        if not offers:
            log.error("No offers found. Check your FUNPAY_USER_ID.")
            await browser.close()
            return

        log.info("Tracking %d offer(s).", len(offers))

        check = 0
        while True:
            check += 1
            log.info("")
            log.info("── Check #%d  (%s) ──────────────────────────────────",
                     check, datetime.now().strftime("%H:%M"))

            # Re-scan profile every hour (every 4 check cycles at 15m interval)
            # to pick up any newly added offers automatically
            if check % 4 == 0:
                log.info("Hourly re-scan for new offers…")
                offers = await discover_offers(page, state)

            boosted_names = []

            for offer in offers:
                url, name = offer["url"], offer["name"]

                if not is_due(state, url):
                    log.info("  ⏳ [%s] — next boost in %s", name, time_remaining(state, url))
                    continue

                log.info("  → Boosting [%s]…", name)
                try:
                    clicked = await boost_page(page, url, name)
                    if clicked:
                        record_boost(state, url, name)
                        boosted_names.append(name)
                    else:
                        # Button was disabled = cooldown still active from a manual boost.
                        # Record now so we don't hammer the page every 15 min.
                        record_boost(state, url, name)
                        log.info("  Recorded cooldown start for [%s].", name)
                except Exception as e:
                    log.error("  Error on [%s]: %s", name, e)

            if boosted_names:
                await tg(
                    "✅ <b>Boosted:</b>\n" +
                    "\n".join(f"  • {n}" for n in boosted_names)
                )

            log.info("Sleeping %dm…", CHECK_INTERVAL_MINUTES)
            await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    asyncio.run(main())
