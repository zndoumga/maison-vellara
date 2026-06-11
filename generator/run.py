"""
CLI entry point for the Maison Vellara data generator.

  python run.py --date 2026-06-10              one full day
  python run.py --backfill 2026-01-01 2026-06-10   day-by-day historical seed
  python run.py --window 9 13 --date 2026-06-10     one intra-day window (live mode)

Phase 1 writes to the local filesystem (SINK_MODE=local). The cloud sinks slot
in behind the same interface in Phase 2 without touching the generators.
"""
from __future__ import annotations

import argparse
import os
from datetime import date

import engine
import seed_masters
from sinks.local_sink import LocalSink
from state import LocalStateStore
from utils.timeutils import daterange


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def build_sink_and_state():
    from dotenv import load_dotenv
    load_dotenv()
    mode = os.environ.get("SINK_MODE", "local")
    if mode == "local":
        out = os.environ.get("OUTPUT_DIR", "./output")
        st = os.environ.get("STATE_DIR", "./state")
        return LocalSink(out), LocalStateStore(st)
    if mode == "cloud":
        from sinks.composite_sink import CompositeSink
        st = os.environ.get("STATE_DIR", "./state")
        return CompositeSink(), LocalStateStore(st)
    raise SystemExit(f"Unknown SINK_MODE={mode}. Use 'local' or 'cloud'.")


def main() -> None:
    p = argparse.ArgumentParser(description="Maison Vellara raw-data generator")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--date", type=_parse_date, help="generate a single day")
    g.add_argument("--backfill", nargs=2, metavar=("START", "END"), help="generate an inclusive date range")
    p.add_argument("--window", nargs=2, type=int, metavar=("START_H", "END_H"),
                   help="restrict to an intra-day hour window (live mode)")
    args = p.parse_args()

    sink, state = build_sink_and_state()
    sink.write_masters(seed_masters.build_masters())

    window = tuple(args.window) if args.window else None

    if args.date:
        days = [args.date]
    else:
        start, end = _parse_date(args.backfill[0]), _parse_date(args.backfill[1])
        days = list(daterange(start, end))

    print(f"Generating {len(days)} day(s)…")
    totals: dict[str, int] = {}
    for d in days:
        summary = engine.run(d, state, sink, window)
        for k, v in summary.items():
            if k == "date":
                continue
            totals[k] = totals.get(k, 0) + v
        idx = days.index(d) + 1
        if len(days) <= 5 or idx % 10 == 0 or d == days[-1]:
            print(
                f"  [{idx}/{len(days)}] {summary['date']}: pos={summary['pos']} clients={summary['clients']} "
                f"inv={summary['inventory']} as={summary['after_sales']} "
                f"ev={summary['ecom_events']} ord={summary['ecom_orders']} "
                f"ret={summary['ecom_returns']} wsf={summary['wholesale_files']} "
                f"st={summary['sellthrough']}"
            )

    state.close()
    print("\nTotals across run:")
    for k, v in totals.items():
        print(f"  {k}: {v}")
    if hasattr(sink, "counts"):
        print(f"\nFiles written under: {os.path.abspath(os.environ.get('OUTPUT_DIR', './output'))}")


if __name__ == "__main__":
    main()
