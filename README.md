# FunPay Auto-Boost 🚀

A **Python** script that automatically clicks the **"Boost offers"** button on all your [FunPay](https://funpay.com) listings every 4 hours — completely hands-free.

## Features

- 🔍 **Auto-detects all your offer categories** — no manual URL setup needed
- ⏱ **Independent timing per offer** — each category tracks its own cooldown; manual boosts are handled gracefully
- 📱 **Optional Telegram notifications** — get a message every time offers are boosted
- 🔄 **Daily log rotation** — logs auto-clean, keeping only the last 3 days
- 🛡 **Cloudflare-resistant** — built-in stealth patches, no extra libraries needed

## Setup

### 1. Install dependencies

Open **PowerShell** and run:

```powershell
pip install playwright
python -m playwright install chromium
```

### 2. Get your `golden_key` cookie

1. Open [funpay.com](https://funpay.com) in Chrome/Edge while logged in
2. Press **F12** → **Application** tab → **Cookies** → `funpay.com`
3. Find `golden_key` → copy its **Value**

> Alternatively: install the [Cookie-Editor](https://cookie-editor.com) browser extension → open FunPay → copy `golden_key`.

The key lasts **100 days**. When it expires, grab a fresh one the same way.

### 3. Get your FunPay user ID

Click your avatar on FunPay → your profile URL will be `funpay.com/en/users/XXXXX/` — the number is your ID.

### 4. Configure the script

Open `funpay_boost.py` and fill in the top section:

```python
GOLDEN_KEY     = "paste_your_golden_key_here"
FUNPAY_USER_ID = "00000"   # your ID from funpay.com/en/users/XXXXX/

CHECK_INTERVAL_MINUTES = 15  # how often to check each offer
BOOST_COOLDOWN_HOURS   = 4   # don't go below 4

# Telegram — leave empty to disable
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID   = ""

HEADLESS = True   # True = fully hidden, False = see the browser
```

That's it — the script finds your offer categories automatically.

### 5. Optional: Telegram notifications

1. Message **@BotFather** on Telegram → `/newbot` → copy the token
2. Message **@userinfobot** on Telegram → copy your chat ID
3. Paste both into the config above

When enabled, you'll receive a Telegram message every time offers are boosted. If Telegram is not configured, notifications go to the CLI log only.

### 6. Run

**Option A — minimized terminal:**
Double-click `START_BOOST.bat`

**Option B — completely hidden (recommended):**
Double-click `START_BOOST.vbs`

### 7. Auto-start with Windows (optional)

Press `Win + R`, type `shell:startup`, hit Enter — drop a shortcut to `START_BOOST.vbs` in that folder. The script will launch automatically every time Windows boots.

## How it works

1. On startup, the script opens your profile page and automatically finds all your offer category links (the pencil icons next to each category)
2. Every 15 minutes it checks each offer independently — if 4 hours have passed since the last boost, it boosts that offer
3. If you manually boost an offer yourself, the script detects the button is on cooldown and reschedules accordingly
4. Every hour it re-scans your profile in case you've added new offers

## Files

| File | Description |
|------|-------------|
| `funpay_boost.py` | Main script |
| `START_BOOST.bat` | Launcher — minimized terminal window |
| `START_BOOST.vbs` | Launcher — completely hidden, no window |
| `boost_state.json` | Auto-created — tracks last boost time per offer |
| `funpay_boost.log` | Auto-created — activity log (rotates daily, 3 days kept) |

## Logs

```
2026-05-31 14:00:01  INFO  ── Check #1  (14:00) ──────────────────────
2026-05-31 14:00:02  INFO  → Boosting [League of Legends Accounts]…
2026-05-31 14:00:06  INFO  ✓ Boosted: [League of Legends Accounts]
2026-05-31 14:00:07  INFO  → Boosting [Where Winds Meet Accounts]…
2026-05-31 14:00:11  INFO  ✓ Boosted: [Where Winds Meet Accounts]
2026-05-31 14:00:11  INFO  Sleeping 15m…
2026-05-31 14:15:01  INFO  ── Check #2  (14:15) ──────────────────────
2026-05-31 14:15:01  INFO  ⏳ [League of Legends Accounts] — next boost in 3h 45m
2026-05-31 14:15:01  INFO  ⏳ [Where Winds Meet Accounts] — next boost in 3h 45m
```

## Notes

- The `golden_key` cookie lasts **100 days** — when expired, grab a fresh one from your browser
- Stealth patches are built-in — no extra libraries, no Cloudflare issues
- Script only accesses your own seller pages

## License

MIT
