#!/usr/bin/env python3
"""
ig-unfollow-campaign.py
=======================
Big Travel Buds — Follow-for-Follow Unfollow Tool

Safely unfollows a list of Instagram accounts using instagrapi,
which emulates a real Android device making Instagram's private API calls.

v2 improvement: fetches your live following list first to get real PKs,
then unfollows by PK only — no public web endpoint lookups that can
trigger Instagram's bot detection.

Features:
  - Resumes where it left off (progress saved after every unfollow)
  - Conservative rate limiting (45-90s delays, 7-12 min batch pauses)
  - 100/day hard cap (reduced from 150 after Instagram warning)
  - Dry-run mode to verify before going live
  - Full log file for tracking

Usage:
  python3 ig-unfollow-campaign.py --sessionid YOUR_SESSION_ID
  python3 ig-unfollow-campaign.py --sessionid YOUR_SESSION_ID --dry-run
  python3 ig-unfollow-campaign.py --sessionid YOUR_SESSION_ID --limit 50

See README.md for how to get your session ID.
"""

import json
import time
import random
import argparse
import logging
from pathlib import Path
from datetime import datetime

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ig-unfollow-campaign.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
FOLLOWLIST_PATH = Path("unfollow-list.json")
PROGRESS_PATH   = Path("ig-unfollow-progress.json")

UNFOLLOW_DELAY_MIN = 45    # seconds between each unfollow (increased from 30)
UNFOLLOW_DELAY_MAX = 90    # seconds (increased from 60)
BATCH_SIZE         = 15    # pause after this many (reduced from 20)
BATCH_PAUSE_MIN    = 420   # 7 min batch pause
BATCH_PAUSE_MAX    = 720   # 12 min batch pause
DAILY_LIMIT        = 100   # reduced from 150 after Instagram warning


# ── Helpers ────────────────────────────────────────────────────────────────────
def load_progress():
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text())
    return {"unfollowed": [], "errors": []}


def save_progress(p):
    PROGRESS_PATH.write_text(json.dumps(p, indent=2))


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="BTB Instagram Unfollow Tool")
    parser.add_argument("--sessionid", required=True,
                        help="Your Instagram sessionid cookie (see README)")
    parser.add_argument("--limit",   type=int, default=DAILY_LIMIT,
                        help=f"Max unfollows this run (default: {DAILY_LIMIT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without actually unfollowing anyone")
    args = parser.parse_args()

    if not FOLLOWLIST_PATH.exists():
        log.error(f"Unfollow list not found: {FOLLOWLIST_PATH}")
        log.error('Create unfollow-list.json: ["username1", "username2"]')
        return

    unfollow_targets = set(json.loads(FOLLOWLIST_PATH.read_text()))
    progress         = load_progress()
    done_set         = set(progress["unfollowed"])
    pending_names    = unfollow_targets - done_set

    log.info("=" * 60)
    log.info("BTB Unfollow Campaign v2")
    log.info(f"  Total in list : {len(unfollow_targets)}")
    log.info(f"  Already done  : {len(done_set)}")
    log.info(f"  Pending       : {len(pending_names)}")
    log.info(f"  Limit this run: {args.limit}")
    log.info(f"  Dry run       : {args.dry_run}")
    log.info("=" * 60)

    if not pending_names:
        log.info("Nothing left to unfollow. Campaign complete! 🎉")
        return

    from instagrapi import Client

    cl = Client()
    cl.login_by_sessionid(args.sessionid)
    me = cl.account_info()
    log.info(f"Logged in as: @{me.username}")

    # Fetch live following list to get real PKs (private API only, no web lookups)
    log.info("Fetching your current following list to resolve PKs...")
    log.info("(This may take a minute if you follow a lot of accounts)")
    following = cl.user_following(me.pk, amount=0)  # 0 = fetch all
    username_to_pk = {u.username.lower(): pk for pk, u in following.items()}
    log.info(f"Found {len(username_to_pk)} accounts you currently follow")

    # Cross-reference — only process accounts we actually still follow
    to_unfollow = []
    skipped_not_following = []
    for username in pending_names:
        pk = username_to_pk.get(username.lower())
        if pk:
            to_unfollow.append((username, pk))
        else:
            skipped_not_following.append(username)

    if skipped_not_following:
        log.info(f"Skipping {len(skipped_not_following)} — already unfollowed or account gone:")
        for u in skipped_not_following:
            log.info(f"  └ @{u}")
        progress["unfollowed"].extend(skipped_not_following)
        save_progress(progress)

    log.info(f"Ready to unfollow: {len(to_unfollow)} accounts")

    done_this_run = 0

    for username, pk in to_unfollow:
        if done_this_run >= args.limit:
            log.info(f"Reached limit of {args.limit} for today. Run again tomorrow.")
            break

        try:
            if args.dry_run:
                log.info(f"[DRY RUN] Would unfollow: @{username} (pk={pk})")
            else:
                cl.user_unfollow(pk)
                log.info(f"Unfollowed: @{username}  [{done_this_run + 1}/{args.limit}]")

            progress["unfollowed"].append(username)
            save_progress(progress)
            done_this_run += 1

        except Exception as e:
            log.error(f"Error on @{username}: {e}")
            progress["errors"].append({
                "username": username,
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            save_progress(progress)
            time.sleep(30)
            continue

        if done_this_run % BATCH_SIZE == 0:
            pause = random.randint(BATCH_PAUSE_MIN, BATCH_PAUSE_MAX)
            log.info(f"Batch of {BATCH_SIZE} complete. Pausing {pause}s...")
            time.sleep(pause)
        else:
            delay = random.randint(UNFOLLOW_DELAY_MIN, UNFOLLOW_DELAY_MAX)
            log.info(f"  (waiting {delay}s...)")
            time.sleep(delay)

    log.info("=" * 60)
    log.info(f"Run complete. Unfollowed {done_this_run} this run.")
    log.info(f"Total unfollowed all-time: {len(set(progress['unfollowed']))}")
    log.info(f"Total errors: {len(progress['errors'])}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()