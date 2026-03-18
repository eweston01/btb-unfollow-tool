#!/usr/bin/env python3
"""
ig-unfollow-campaign.py
=======================
Big Travel Buds — Follow-for-Follow Unfollow Tool

Safely unfollows a list of Instagram accounts using instagrapi,
which emulates a real Android device making private API calls.

Features:
  - Resumes where it left off (progress saved after every unfollow)
  - Conservative rate limiting (30-60s delays, 5-10 min batch pauses)
  - 150/day hard cap to stay under Instagram's unofficial limit
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
FOLLOWLIST_PATH = Path("unfollow-list.json")   # list of username strings
PROGRESS_PATH   = Path("ig-unfollow-progress.json")

UNFOLLOW_DELAY_MIN = 30    # seconds between each unfollow
UNFOLLOW_DELAY_MAX = 60
BATCH_SIZE         = 20    # pause after this many unfollows
BATCH_PAUSE_MIN    = 300   # 5 min batch pause
BATCH_PAUSE_MAX    = 600   # 10 min batch pause
DAILY_LIMIT        = 150   # Instagram's safe daily unfollow cap


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
                        help="Your Instagram sessionid cookie (see README for how to get this)")
    parser.add_argument("--limit",   type=int, default=DAILY_LIMIT,
                        help=f"Max unfollows this run (default: {DAILY_LIMIT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without actually unfollowing anyone")
    args = parser.parse_args()

    if not FOLLOWLIST_PATH.exists():
        log.error(f"Unfollow list not found: {FOLLOWLIST_PATH}")
        log.error("Create a file called unfollow-list.json with a list of usernames.")
        log.error('Example: ["username1", "username2", "username3"]')
        return

    followlist = json.loads(FOLLOWLIST_PATH.read_text())
    progress   = load_progress()
    done_set   = set(progress["unfollowed"])
    pending    = [u for u in followlist if u not in done_set]

    log.info("=" * 60)
    log.info("BTB Unfollow Campaign")
    log.info(f"  Total in list : {len(followlist)}")
    log.info(f"  Already done  : {len(done_set)}")
    log.info(f"  Pending       : {len(pending)}")
    log.info(f"  Limit this run: {args.limit}")
    log.info(f"  Dry run       : {args.dry_run}")
    log.info("=" * 60)

    if not pending:
        log.info("Nothing left to unfollow. Campaign complete! 🎉")
        return

    from instagrapi import Client

    cl = Client()
    cl.login_by_sessionid(args.sessionid)
    me = cl.account_info()
    log.info(f"Logged in as: @{me.username}")

    done_this_run = 0

    for username in pending:
        if done_this_run >= args.limit:
            log.info(f"Reached limit of {args.limit} for today. Run again tomorrow to continue.")
            break

        try:
            user_info = cl.user_info_by_username(username)

            if args.dry_run:
                log.info(f"[DRY RUN] Would unfollow: @{username}")
            else:
                cl.user_unfollow(user_info.pk)
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
            time.sleep(15)
            continue

        # Batch pause every N unfollows
        if done_this_run % BATCH_SIZE == 0:
            pause = random.randint(BATCH_PAUSE_MIN, BATCH_PAUSE_MAX)
            log.info(f"Batch of {BATCH_SIZE} complete. Pausing {pause}s before next batch...")
            time.sleep(pause)
        else:
            time.sleep(random.randint(UNFOLLOW_DELAY_MIN, UNFOLLOW_DELAY_MAX))

    log.info("=" * 60)
    log.info(f"Run complete. Unfollowed {done_this_run} this run.")
    log.info(f"Total unfollowed all-time: {len(set(progress['unfollowed']))}")
    log.info(f"Total errors: {len(progress['errors'])}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
