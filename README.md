# BTB Instagram Unfollow Tool

A safe, resumable script to bulk-unfollow accounts from a follow-for-follow campaign.
Built for the Big Travel Buds group — works on Mac, Linux, or Windows.

---

## How it works

This tool uses **[instagrapi](https://github.com/subzeroid/instagrapi)**, a Python library
that emulates a real Android device making Instagram's private API calls. It mimics the
same requests your phone sends — not a browser bot, not the public API. This is why it's
more stable than most Instagram automation tools.

> ⚠️ **Fair warning:** Bulk unfollowing is against Instagram's Terms of Service.
> This tool uses conservative rate limits to minimize risk, but use it at your own discretion.
> Never share your session ID with anyone.

---

## Prerequisites

### 1. Python 3.10 or higher

Check if you have it:
```bash
python3 --version
```

If not:
- **Mac:** `brew install python` (or download from [python.org](https://python.org))
- **Windows:** Download from [python.org](https://python.org)
- **Linux/Debian:** `sudo apt install python3 python3-pip`

---

### 2. The instagrapi patch

instagrapi's `login_by_sessionid` method calls a deprecated Instagram endpoint that will
cause an error without this fix. Apply it once after install:

```bash
pip install instagrapi==2.1.3

# Find where instagrapi is installed
python3 -c "import instagrapi; print(instagrapi.__file__)"
```

Open the `auth.py` file in that directory, find these lines (around line 369):

```python
# ORIGINAL (broken) — looks something like this:
self.private.headers.update(...)
self.login_flow()
```

And add a bypass so `login_by_sessionid` skips the deprecated `si:` challenge flow.
The exact lines to patch depend on your version — see the
[instagrapi issue tracker](https://github.com/subzeroid/instagrapi/issues) for the
current fix if you hit a `login_flow` error.

**Quick test to confirm your install is working:**
```bash
python3 -c "from instagrapi import Client; print('instagrapi OK')"
```

---

### 3. Your Instagram Session ID (not your password)

The script authenticates using your session cookie — never your password.
This is safer because the session ID expires automatically and can be revoked
just by logging out.

**How to get your session ID:**

1. Open Chrome and log into Instagram
2. Press **F12** (or right-click → Inspect)
3. Go to **Application** tab
4. In the left sidebar: **Cookies** → `https://www.instagram.com`
5. Find the cookie named **`sessionid`**
6. Copy the full value (it's a long string like `12345678%3AaBcXyZ%3A22%3A...`)

> Keep this value private. Anyone with your session ID can access your account.
> It expires when you log out of Instagram on that browser.

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/btb-unfollow-tool.git
cd btb-unfollow-tool

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your unfollow list
# Copy sample-unfollow-list.json to unfollow-list.json and replace with your usernames
cp sample-unfollow-list.json unfollow-list.json
```

Edit `unfollow-list.json` — it's just a list of usernames (no @ symbol):

```json
[
  "username_one",
  "username_two",
  "username_three"
]
```

---

## Running the script

**Always do a dry run first:**
```bash
python3 ig-unfollow-campaign.py --sessionid "YOUR_SESSION_ID" --dry-run
```

This prints every account it would unfollow without actually doing anything.
Confirm the list looks right, then run for real:

**Real run — start conservative:**
```bash
python3 ig-unfollow-campaign.py --sessionid "YOUR_SESSION_ID" --limit 50
```

**Next day — it resumes automatically:**
```bash
python3 ig-unfollow-campaign.py --sessionid "YOUR_SESSION_ID" --limit 100
```

---

## Rate limits

The script is intentionally slow to stay safe:

| Setting | Value |
|---|---|
| Delay between unfollows | 30–60 seconds (random) |
| Pause every 20 unfollows | 5–10 minutes |
| Daily hard cap | 150 accounts |

Instagram's unofficial safe limit is around 150–200 unfollows per day.
Going faster risks a temporary action block on your account.

---

## Progress & resuming

Progress is saved to `ig-unfollow-progress.json` after **every single unfollow**.
It's safe to Ctrl+C at any time — just run the script again and it picks up
exactly where it left off.

**Check your progress anytime:**
```bash
python3 -c "
import json
p = json.load(open('ig-unfollow-progress.json'))
print(f'Unfollowed: {len(p[\"unfollowed\"])}')
print(f'Errors:     {len(p[\"errors\"])}')
print(f'Last 3:     {p[\"unfollowed\"][-3:]}')
"
```

**Full log** is written to `ig-unfollow-campaign.log`.

---

## Troubleshooting

**`login_by_sessionid` error / challenge required**
Your session ID has expired. Go back to Chrome DevTools and grab a fresh one.
This happens if Instagram logged you out or the session timed out.

**`ChallengeRequired` or `429 Too Many Requests`**
You've been rate-limited. Stop the script, wait 24 hours, then resume with a
lower `--limit` (try 30–50).

**User not found errors**
The account was deleted or changed their username since the list was made.
These are logged to `errors` in the progress file and skipped automatically.

---

## Files

| File | Purpose |
|---|---|
| `ig-unfollow-campaign.py` | Main script |
| `unfollow-list.json` | Your list of usernames to unfollow *(gitignored — stays private)* |
| `sample-unfollow-list.json` | Example format |
| `ig-unfollow-progress.json` | Auto-generated progress tracker *(gitignored)* |
| `ig-unfollow-campaign.log` | Auto-generated run log *(gitignored)* |

---

## License

MIT — use freely, modify as needed.
