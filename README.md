# FunPay Auto-Boost 🚀

A **Python** script that automatically clicks the **"Boost offers"** button on your [FunPay](https://funpay.com) listings every 4 hours — completely hands-free.

## How it works

- Uses your `golden_key` session cookie to authenticate (no password stored)
- Opens a hidden Chromium browser via Playwright
- Navigates to each of your offer pages and clicks Boost
- Sleeps 4 hours, then repeats
- Writes a log file so you can check activity anytime

## Setup

### 1. Install dependencies

Open **cmd** and run:

```powershell
pip install playwright
python -m playwright install chromium
```

### 2. Get your `golden_key` cookie

1. Open [funpay.com](https://funpay.com) in Chrome/Edge while logged in
2. Press **F12** → **Application** tab → **Cookies** → `funpay.com`
3. Find `golden_key` → copy its **Value** (**DO NOT share your golden_key. It gives full unrestricted access to your funpay.com account, keep it safe on your local machine!**)
   
> Alternatively: install the [Cookie-Editor](https://cookie-editor.com) browser extension, open FunPay, and copy `golden_key` from there.

### 3. Configure the script

Open `funpay_boost.py` and edit the top section:

```python
GOLDEN_KEY = "paste_your_golden_key_here"   # from step 2

OFFERS_PAGES = [
    "https://funpay.com/en/lots/YOUR_LOT_ID/trade",  # replace with your lot URLs
]

BOOST_EVERY_HOURS = 4    # don't go below 4 (FunPay's cooldown)
HEADLESS          = True # True = fully hidden, False = see the browser
```

### 4. Run

**Option A — visible terminal (minimized):**
Double-click `START_BOOST.bat`

**Option B — completely invisible (no window at all):**
Double-click `START_BOOST.vbs`

### 5. Auto-start with Windows (optional)

Press `Win + R`, type `shell:startup`, hit Enter — drop a shortcut to `START_BOOST.vbs` in that folder. Script will launch automatically every time Windows boots.

## Files

| File | Description |
|------|-------------|
| `funpay_boost.py` | Main script |
| `START_BOOST.bat` | Launcher — minimized terminal window |
| `START_BOOST.vbs` | Launcher — completely hidden, no window |

## Logs

Activity is saved to `funpay_boost.log` in the same folder. Open it anytime to see the last boost times and any errors.

```
2026-05-30 14:00:01  INFO      ── Cycle #1 ─────────────────────────────────────
2026-05-30 14:00:03  INFO      Opening: https://funpay.com/en/lots/[ID]/trade
2026-05-30 14:00:07  INFO      ✓ Boosted: https://funpay.com/en/lots/[ID]/trade
2026-05-30 14:00:09  INFO      ✓ Boosted: https://funpay.com/en/lots/[ID]/trade
2026-05-30 14:00:09  INFO      Sleeping 4h until next boost…
```

## Notes

- The `golden_key` cookie lasts **100 days** — when it expires, grab a fresh one from your browser
- Stealth patches are built-in to avoid Cloudflare bot detection
- Script only accesses your own seller pages — no scraping or abuse of FunPay's platform

## License

MIT
