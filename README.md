# Maison Vellara — End-to-End Data Platform

A portfolio data-engineering project for the **luxury leather-goods** sector. It
simulates a fictional maison, *Maison Vellara*, and runs realistic raw data from
three genuinely different source systems all the way to Power BI in Microsoft
Fabric, transformed with dbt.

The point is **realism**: the generated data looks like raw operational exports
(messy, nested, multi-format, multi-currency, with returns, corrections,
stockouts and late-arriving records) — *not* pre-built dimensional tables. The
modelling is left for dbt, exactly as in a real engagement.

## Three sources, three ingestion patterns

| # | Channel | System | Storage | Fabric reads via | Shape |
|---|---------|--------|---------|------------------|-------|
| 1 | Boutiques | POS / CRM / Inventory / After-sales | Supabase (Postgres) | Postgres connector | relational tables |
| 2 | Online store | Shopify-like platform | Firebase → FastAPI on Render | HTTP/REST connector | nested JSON |
| 3 | Wholesale | 3 French department stores | Azure Blob (files) + portal API | Blob + HTTP connectors | per-partner CSV dialects + per-partner JSON |

8 boutiques across 8 cities · 28 advisors · 86 SKUs · 3 wholesale partners
(Galeries Lafayette, Le Bon Marché, Printemps).

## Repository

```
generator/   Python data generator (this is the engine)
supabase/    Postgres DDL (Phase 2)
api/         FastAPI serving the online store + partner portals (Phase 2)
dashboard/   Next.js live dashboard on Vercel (Phase 2)
dbt/         raw → staging → mart models (Phase 2)
docs/        Fabric + Power BI runbook (Phase 2)
```

## Running the generator (local, no credentials)

```bash
cd generator
pip install -r requirements.txt
python run.py --date 2026-06-10                  # one day
python run.py --backfill 2026-01-01 2026-06-10   # historical seed
python run.py --window 9 13 --date 2026-06-10    # one intra-day window (live mode)
```

Output lands under `generator/output/` mirroring the cloud layout. Generator
state (clients, inventory positions, open repairs, partner stock) persists in
`generator/state/state.db` so the simulated world evolves coherently day to day.

### Realism features baked in
- Multi-currency boutique pricing (EUR/GBP/USD/JPY/AED/CHF) by store
- Seasonality (Dec peak, Aug dip, fashion-week bumps) + day-of-week footfall
- 5–8% anonymous till transactions; ~4% returns; 1–3% French *factures
  rectificatives* (correcting invoices — originals never deleted)
- Inventory depletion, reorders, 3–7 day replenishment, transient negative stock
- Online funnel (session → view → cart → checkout) with ~5% payment failures
- Online customers that partially overlap boutique CRM (identity resolution is
  a dbt problem — the generator never links them)
- Three independent wholesale file dialects and three independent sell-through
  JSON shapes; some days a partner portal is "down"
- Localised names/emails/phones by client nationality (romanised email aliases
  for non-latin names)

## Status

- **Phase 1 — generator core: complete.** Runs locally end-to-end.
- Phase 2 — cloud sinks, API, backfill, Railway, dashboard, dbt, Fabric: pending
  credentials (see `generator/.env.example`).
