"""
Railway always-on scheduler.

Runs every 45 minutes, generating data for the current intra-day window so
that events accumulate realistically throughout the day rather than all
appearing at once. At midnight it rolls over to a new date automatically.

State persists in /data/state.db (Railway persistent volume) so the world
evolves coherently across restarts.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, date

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# On Railway, state lives on the persistent volume at /data
STATE_DIR = os.environ.get("STATE_DIR", "/data/state")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/tmp/output")  # not used in cloud mode


def run_window():
    """Generate one 45-minute window for the current date."""
    import engine
    import seed_masters
    from sinks.composite_sink import CompositeSink
    from state import LocalStateStore

    now = datetime.now(timezone.utc)
    today = now.date()
    hour = now.hour

    # Window covers the last 45 minutes rounded to the hour
    window_start = max(0, hour - 1)
    window_end = hour + 1

    log.info(f"Generating window {window_start}h-{window_end}h for {today}")

    sink = CompositeSink()
    state = LocalStateStore(STATE_DIR)

    try:
        sink.write_masters(seed_masters.build_masters())
        summary = engine.run(today, state, sink, window=(window_start, window_end))
        log.info(
            f"Done — pos={summary['pos']} clients={summary['clients']} "
            f"ecom_orders={summary['ecom_orders']} ecom_events={summary['ecom_events']} "
            f"sellthrough={summary['sellthrough']}"
        )
    except Exception as e:
        log.error(f"Window generation failed: {e}", exc_info=True)
    finally:
        state.close()
        sink.close()


if __name__ == "__main__":
    log.info("Maison Vellara scheduler starting...")
    os.makedirs(STATE_DIR, exist_ok=True)

    # Run immediately on startup so Railway deploys produce data right away
    run_window()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_window, "interval", minutes=45, id="data_window")
    log.info("Scheduler running — every 45 minutes")
    scheduler.start()
