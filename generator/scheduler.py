"""
Railway nightly batch scheduler.

Once per day (02:00 UTC) it generates every COMPLETE day that hasn't been
generated yet — i.e. all days strictly before today (UTC). It never generates a
partial current day, so each morning exactly one clean, full day appears.

State lives in Supabase (generator_state schema) — a single shared source of
truth with the historical backfill, so there are no ID collisions and the world
evolves coherently. A `last_generated_date` cursor in state tracks progress and
lets the job catch up if Railway was down for a few days.

The scheduler will not run until the state has been seeded (cursor present);
this prevents a fresh Railway deploy from initialising a conflicting world
before the backfill state has been synced in.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, date, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scheduler")


def run_pending_days():
    import engine
    import seed_masters
    from sinks.composite_sink import CompositeSink
    from state_supabase import SupabaseStateStore

    sink = CompositeSink()
    state = SupabaseStateStore()

    cursor = state.get_meta("last_generated_date")
    if not cursor:
        log.warning("No 'last_generated_date' in state — not seeded yet. Skipping. "
                    "Run sync_state_to_supabase.py from the backfill machine first.")
        return

    last = date.fromisoformat(cursor)
    today = datetime.now(timezone.utc).date()
    target = last + timedelta(days=1)

    if target >= today:
        log.info(f"Nothing to do — last generated {last}, today is {today} (current day not yet complete).")
        return

    sink.write_masters(seed_masters.build_masters())
    while target < today:
        log.info(f"Generating full day {target} …")
        summary = engine.run(target, state, sink)  # full-day, replace-by-date
        log.info(f"  done — pos={summary['pos']} clients={summary['clients']} "
                 f"ecom_orders={summary['ecom_orders']} sellthrough={summary['sellthrough']}")
        target += timedelta(days=1)

    sink.close()
    log.info("Catch-up complete.")


if __name__ == "__main__":
    log.info("Maison Vellara nightly scheduler starting…")
    try:
        run_pending_days()  # catch up on startup
    except Exception as e:
        log.error(f"Startup run failed: {e}", exc_info=True)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_pending_days, "cron", hour=2, minute=0, id="nightly")
    log.info("Scheduler armed — nightly at 02:00 UTC")
    scheduler.start()
