# Maison Vellara — Microsoft Fabric Runbook

End-to-end guide for setting up the Fabric ingestion layer, dbt transformations, and Power BI reports on top of the three Maison Vellara source systems.

---

## Architecture Overview

```
SOURCE SYSTEMS                BRONZE LAKEHOUSE           SILVER           GOLD
─────────────────             ─────────────────          ──────           ────
Supabase (Postgres)
  pos.transactions   ──────►  tbl_pos_transactions
  crm.clients        ──────►  tbl_crm_clients
  inventory.*        ──────►  tbl_inventory_snapshots    stg_*    ──►    fct_*
  after_sales.*      ──────►  tbl_after_sales_orders     int_*    ──►    dim_*
  ref.*              ──────►  tbl_ref_*

Azure Blob Storage
  wholesale/*.csv  shortcut►  raw files (read-only ref)
  via notebooks    ──────►    tbl_wholesale_glf_po
                              tbl_wholesale_lbm_po
                              tbl_wholesale_prt_po
                              tbl_wholesale_*_sellthrough

FastAPI (Render)
  /ecom/orders     ──────►    raw JSON files
  /ecom/events     ──────►    raw JSON files
  /ecom/returns    via ──►    tbl_ecom_orders
  /wholesale/*/             notebooks  tbl_ecom_events
   sellthrough               ──────►   tbl_ecom_returns
```

**Key principle:** Everything in Bronze is a Delta table. Files (CSVs from Blob, JSONs from API) are parsed by PySpark notebooks and written as Delta tables before dbt touches anything.

---

## Fabric Workspace Setup

1. Go to [app.fabric.microsoft.com](https://app.fabric.microsoft.com)
2. Create workspace: **maison-vellara**
3. Create three Lakehouses inside it:
   - `bronze` — raw ingestion layer
   - `silver` — cleaned staging tables
   - `gold` — business-ready dims and facts

---

## Step 1 — Blob Storage Shortcut (Wholesale CSVs)

The shortcut gives Fabric read access to the raw CSV files in Azure Blob without copying them. Notebooks will read from this shortcut.

1. Open the **bronze** Lakehouse
2. **New shortcut** → **Azure Data Lake Storage Gen2**
3. Connection settings:
   - URL: `https://maisonvellara.blob.core.windows.net`
   - Authentication: Account Key (from Azure portal → Storage account → Access keys)
   - Shortcut name: `wholesale_raw`
   - Target path: `/wholesale`
4. The shortcut appears under `Files/wholesale_raw/` in the Bronze Lakehouse
5. Files are organized as:
   ```
   Files/wholesale_raw/
     GLF/po/GLF-2026-*.csv
     LBM/po/LBM-2026-*.csv
     PRT/po/PRT-2026-*.csv
   ```

---

## Step 2 — Pipeline A: Supabase → Bronze Tables

Creates a Fabric Data Pipeline that pulls all Supabase tables into Bronze Delta tables daily.

### Create the pipeline

1. Workspace → **New** → **Data Pipeline** → name: `ingest_supabase_daily`

### Configure Postgres connection

1. Add activity: **Copy data**
2. Source → **New connection** → **PostgreSQL**
   - Server: `aws-0-eu-west-3.pooler.supabase.com`
   - Port: `6543`
   - Database: `postgres`
   - Username: `postgres.yflnqktrbeexovkwxayc`
   - Password: from `.env` → `SUPABASE_DB_PASSWORD`
3. Save connection as `supabase_maison_vellara`

### Tables to copy

Add one Copy Data activity per table (or use ForEach with a list):

| Source schema.table | Bronze table name |
|---|---|
| `pos.transactions` | `tbl_pos_transactions` |
| `crm.clients` | `tbl_crm_clients` |
| `inventory.snapshots` | `tbl_inventory_snapshots` |
| `after_sales.orders` | `tbl_after_sales_orders` |
| `ref.stores` | `tbl_ref_stores` |
| `ref.advisors` | `tbl_ref_advisors` |
| `ref.technicians` | `tbl_ref_technicians` |
| `ref.products` | `tbl_ref_products` |

For each:
- Destination: **bronze** Lakehouse → Tables → `tbl_*` (name as above)
- Write mode: **Overwrite** (full refresh daily)

### Schedule

- Trigger: **New schedule trigger** → Daily → 03:00 UTC

---

## Step 3 — Pipeline B: FastAPI → Bronze JSON Files

Calls the FastAPI endpoints and lands raw JSON responses as files in the Bronze Lakehouse. A notebook then converts them to Delta tables.

### Create the pipeline

1. New Pipeline → `ingest_api_daily`
2. Add a **Set variable** activity at the start:
   - Variable name: `run_date`
   - Value: `@formatDateTime(utcNow(), 'yyyy-MM-dd')`

### Ecom endpoints

Add one **Copy data** activity per endpoint:

| Endpoint | Output file path |
|---|---|
| `/ecom/orders?date=@{variables('run_date')}` | `Files/api_raw/ecom/orders/@{variables('run_date')}.json` |
| `/ecom/events?date=@{variables('run_date')}` | `Files/api_raw/ecom/events/@{variables('run_date')}.json` |
| `/ecom/returns?date=@{variables('run_date')}` | `Files/api_raw/ecom/returns/@{variables('run_date')}.json` |

For each Copy Data source:
- Type: **HTTP**
- Base URL: `https://maison-vellara.onrender.com`
- Relative URL: (endpoint path above)
- Method: GET
- Headers: `{"x-api-key": "<API_KEY — see generator/.env>"}`
- Authentication: None (API key is in the header)

### Wholesale sell-through endpoints

Same pattern for:

| Endpoint | Output file path |
|---|---|
| `/wholesale/glf/sellthrough?date=@{variables('run_date')}` | `Files/api_raw/wholesale/glf/@{variables('run_date')}.json` |
| `/wholesale/lbm/sellthrough?date=@{variables('run_date')}` | `Files/api_raw/wholesale/lbm/@{variables('run_date')}.json` |
| `/wholesale/prt/sellthrough?date=@{variables('run_date')}` | `Files/api_raw/wholesale/prt/@{variables('run_date')}.json` |

> **Note:** Render free tier cold-starts in ~30s. Set HTTP timeout to 60s in the connection settings.

### Schedule

- Trigger: Daily → 03:30 UTC

---

## Step 4 — Notebook A: Parse Wholesale CSVs → Bronze Tables

This notebook reads the 3 wholesale partner CSV dialects from the shortcut and writes conformed Delta tables into Bronze.

### Create the notebook

1. Workspace → **New** → **Notebook** → name: `nb_parse_wholesale_csvs`
2. Attach to **bronze** Lakehouse

### Notebook code

```python
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import date

today = date.today().isoformat()

# ── GLF: uppercase FR headers, comma-delimited ──────────────────────────────
glf_raw = (spark.read.option("header", True).option("delimiter", ",")
           .csv("Files/wholesale_raw/GLF/po/"))

glf = (glf_raw
       .withColumnRenamed("NUMERO_COMMANDE", "po_number")
       .withColumnRenamed("DATE_COMMANDE", "order_date")
       .withColumnRenamed("REFERENCE_PRODUIT", "sku_id")
       .withColumnRenamed("QUANTITE", "quantity")
       .withColumnRenamed("PRIX_UNITAIRE", "unit_price")
       .withColumnRenamed("DEVISE", "currency")
       .withColumnRenamed("NOM_CLIENT", "customer_name")
       .withColumnRenamed("TELEPHONE", "customer_phone")
       .withColumnRenamed("EMAIL", "customer_email")
       .withColumnRenamed("PAYS", "customer_country")
       .withColumn("partner_id", F.lit("GLF"))
       .withColumn("_load_date", F.lit(today)))

glf.write.format("delta").mode("overwrite").saveAsTable("tbl_wholesale_glf_po")

# ── LBM: lowercase EN/FR mix, ISO dates ──────────────────────────────────────
lbm_raw = (spark.read.option("header", True).option("delimiter", ",")
           .csv("Files/wholesale_raw/LBM/po/"))

lbm = (lbm_raw
       .withColumnRenamed("order_ref", "po_number")
       .withColumnRenamed("order_date", "order_date")
       .withColumnRenamed("sku", "sku_id")
       .withColumnRenamed("qty", "quantity")
       .withColumnRenamed("price_eur", "unit_price")
       .withColumnRenamed("currency", "currency")
       .withColumnRenamed("client_name", "customer_name")
       .withColumnRenamed("client_phone", "customer_phone")
       .withColumnRenamed("client_email", "customer_email")
       .withColumnRenamed("client_country", "customer_country")
       .withColumn("partner_id", F.lit("LBM"))
       .withColumn("_load_date", F.lit(today)))

lbm.write.format("delta").mode("overwrite").saveAsTable("tbl_wholesale_lbm_po")

# ── PRT: semicolon-delimited, DDMMYYYY dates, comma decimals ─────────────────
prt_raw = (spark.read.option("header", True).option("delimiter", ";")
           .csv("Files/wholesale_raw/PRT/po/"))

prt = (prt_raw
       .withColumnRenamed("ref_cmd", "po_number")
       .withColumn("order_date",
           F.to_date(F.col("dt_cmd"), "ddMMyyyy"))
       .withColumnRenamed("code_article", "sku_id")
       .withColumnRenamed("qte", "quantity")
       .withColumn("unit_price",
           F.regexp_replace("px_unitaire", ",", ".").cast("double"))
       .withColumnRenamed("devise", "currency")
       .withColumnRenamed("nom_acheteur", "customer_name")
       .withColumnRenamed("tel_acheteur", "customer_phone")
       .withColumnRenamed("mail_acheteur", "customer_email")
       .withColumnRenamed("pays_acheteur", "customer_country")
       .withColumn("partner_id", F.lit("PRT"))
       .withColumn("_load_date", F.lit(today)))

prt.write.format("delta").mode("overwrite").saveAsTable("tbl_wholesale_prt_po")

print("Wholesale CSVs parsed and written to Bronze tables.")
```

---

## Step 5 — Notebook B: Parse API JSONs → Bronze Tables

Reads the JSON files landed by Pipeline B and writes Delta tables into Bronze.

### Create the notebook

1. New Notebook → `nb_parse_api_jsons`
2. Attach to **bronze** Lakehouse

### Notebook code

```python
from pyspark.sql import functions as F
from datetime import date

today = date.today().isoformat()

# ── Ecom orders (nested JSON with line_items array) ──────────────────────────
orders_raw = spark.read.json(f"Files/api_raw/ecom/orders/{today}.json")

orders = (orders_raw
          .select(
              "order_id", "order_date", "client_id", "client_email",
              "financial_status", "device_type", "channel", "total_amount",
              F.col("shipping_address.country").alias("shipping_country"),
              F.explode("line_items").alias("line")
          )
          .select("*",
              F.col("line.sku_id").alias("sku_id"),
              F.col("line.quantity").alias("quantity"),
              F.col("line.unit_price").alias("unit_price"))
          .drop("line")
          .withColumn("_load_date", F.lit(today)))

orders.write.format("delta").mode("append").saveAsTable("tbl_ecom_orders")

# ── Ecom events (clickstream) ─────────────────────────────────────────────────
events_raw = spark.read.json(f"Files/api_raw/ecom/events/{today}.json")

events = (events_raw
          .select("session_id", "client_id", "event_type", "event_ts",
                  "sku_id", "referrer", "device_type", "country")
          .withColumn("_load_date", F.lit(today)))

events.write.format("delta").mode("append").saveAsTable("tbl_ecom_events")

# ── Ecom returns ──────────────────────────────────────────────────────────────
returns_raw = spark.read.json(f"Files/api_raw/ecom/returns/{today}.json")

returns = (returns_raw
           .select("return_id", "order_id", "return_date", "reason_code",
                   "sku_id", "quantity", "refund_amount")
           .withColumn("_load_date", F.lit(today)))

returns.write.format("delta").mode("append").saveAsTable("tbl_ecom_returns")

# ── Wholesale sell-through (3 shapes) ─────────────────────────────────────────

# GLF: array of objects
glf_raw = spark.read.json(f"Files/api_raw/wholesale/glf/{today}.json")
glf_st = (glf_raw
          .select("sku_id", "date", "qty_sold", "qty_on_hand",
                  "customer_name", "customer_phone", "customer_email", "customer_country")
          .withColumn("partner_id", F.lit("GLF"))
          .withColumn("_load_date", F.lit(today)))
glf_st.write.format("delta").mode("append").saveAsTable("tbl_wholesale_sellthrough")

# LBM: keyed object — flatten with stack or explode map
lbm_raw = spark.read.json(f"Files/api_raw/wholesale/lbm/{today}.json")
lbm_st = (lbm_raw
          .select(F.explode("items").alias("item"))
          .select(
              F.col("item.sku").alias("sku_id"),
              F.col("item.report_date").alias("date"),
              F.col("item.units_sold").alias("qty_sold"),
              F.col("item.stock_remaining").alias("qty_on_hand"),
              F.col("item.buyer_name").alias("customer_name"),
              F.col("item.buyer_phone").alias("customer_phone"),
              F.col("item.buyer_email").alias("customer_email"),
              F.col("item.buyer_country").alias("customer_country"))
          .withColumn("partner_id", F.lit("LBM"))
          .withColumn("_load_date", F.lit(today)))
lbm_st.write.format("delta").mode("append").saveAsTable("tbl_wholesale_sellthrough")

# PRT: flat short-key array
prt_raw = spark.read.json(f"Files/api_raw/wholesale/prt/{today}.json")
prt_st = (prt_raw
          .select(
              F.col("ref").alias("sku_id"),
              F.col("dt").alias("date"),
              F.col("vte").alias("qty_sold"),
              F.col("stk").alias("qty_on_hand"),
              F.col("nm").alias("customer_name"),
              F.col("tel").alias("customer_phone"),
              F.col("ml").alias("customer_email"),
              F.col("pays").alias("customer_country"))
          .withColumn("partner_id", F.lit("PRT"))
          .withColumn("_load_date", F.lit(today)))
prt_st.write.format("delta").mode("append").saveAsTable("tbl_wholesale_sellthrough")

print("API JSONs parsed and written to Bronze tables.")
```

---

## Step 6 — Master Orchestration Pipeline

One pipeline chains everything in the correct order.

1. New Pipeline → `orchestrate_daily`
2. Add activities in sequence with **On success** dependencies:

```
[03:00] ingest_supabase_daily
           ↓ on success
[03:30] ingest_api_daily
           ↓ on success
[04:00] nb_parse_wholesale_csvs  (Execute Pipeline / Notebook activity)
           ↓ on success
[04:15] nb_parse_api_jsons
           ↓ on success
[04:30] dbt_build  (see Step 7)
```

3. Schedule trigger: Daily 03:00 UTC (subsequent steps trigger by dependency, not clock)

---

## Step 7 — dbt Setup

dbt transforms Bronze Delta tables → Silver (stg_*) → intermediate (int_*) → Gold (fct_*, dim_*).

### Project structure

```
dbt/
  dbt_project.yml
  profiles.yml          ← Fabric Lakehouse connection
  models/
    sources.yml         ← declares Bronze tables as sources
    staging/
      stg_boutique_sales.sql
      stg_crm_clients.sql
      stg_inventory_snapshots.sql
      stg_after_sales_orders.sql
      stg_ecom_orders.sql
      stg_ecom_events.sql
      stg_ecom_returns.sql
      stg_wholesale_po.sql         ← unions GLF + LBM + PRT
      stg_wholesale_sellthrough.sql
      stg_ref_*.sql
    intermediate/
      int_omnichannel_customers.sql    ← identity resolution (email/phone match)
      int_customer_spend.sql           ← cumulative spend for VIP tier
    marts/
      dim_customers.sql
      dim_date.sql
      dim_store.sql
      dim_product.sql
      dim_advisor.sql
      dim_wholesale_partner.sql
      fct_boutique_sales.sql
      fct_inventory_daily.sql
      fct_after_sales.sql
      fct_ecom_orders.sql
      fct_wholesale_orders.sql
      fct_wholesale_sellthrough_daily.sql
```

### sources.yml (Bronze tables)

```yaml
version: 2

sources:
  - name: bronze
    schema: bronze
    tables:
      - name: tbl_pos_transactions
      - name: tbl_crm_clients
      - name: tbl_inventory_snapshots
      - name: tbl_after_sales_orders
      - name: tbl_ref_stores
      - name: tbl_ref_advisors
      - name: tbl_ref_technicians
      - name: tbl_ref_products
      - name: tbl_ecom_orders
      - name: tbl_ecom_events
      - name: tbl_ecom_returns
      - name: tbl_wholesale_glf_po
      - name: tbl_wholesale_lbm_po
      - name: tbl_wholesale_prt_po
      - name: tbl_wholesale_sellthrough
```

### Key staging models

**`stg_wholesale_po.sql`** — unions 3 partner tables into one conformed table:
```sql
select 'GLF' as partner_id, po_number, order_date, sku_id, quantity,
       unit_price, currency, customer_name, customer_phone, customer_email,
       customer_country, _load_date
from {{ source('bronze', 'tbl_wholesale_glf_po') }}

union all

select 'LBM', po_number, order_date, sku_id, quantity,
       unit_price, currency, customer_name, customer_phone, customer_email,
       customer_country, _load_date
from {{ source('bronze', 'tbl_wholesale_lbm_po') }}

union all

select 'PRT', po_number, order_date, sku_id, quantity,
       unit_price, currency, customer_name, customer_phone, customer_email,
       customer_country, _load_date
from {{ source('bronze', 'tbl_wholesale_prt_po') }}
```

**`int_omnichannel_customers.sql`** — links boutique CRM clients to ecom accounts:
```sql
-- Boutique clients matched to ecom accounts by email or phone
-- No match = two separate records; matching happens here, not in the generator
select
    coalesce(c.client_id, e.client_id) as unified_client_id,
    c.client_id as crm_client_id,
    e.client_id as ecom_client_id,
    coalesce(c.email, e.email) as email,
    coalesce(c.phone, e.phone) as phone,
    coalesce(c.nationality, e.country) as nationality,
    case when c.client_id is not null and e.client_id is not null
         then 'omnichannel'
         when c.client_id is not null then 'boutique_only'
         else 'ecom_only'
    end as channel_presence
from {{ ref('stg_crm_clients') }} c
full outer join {{ ref('stg_ecom_orders') }} e
    on lower(c.email) = lower(e.client_email)
    or c.phone = e.client_phone
```

---

## Step 8 — Power BI

1. Open Power BI in Fabric workspace
2. **New report** → connect to **gold** Lakehouse
3. Import all `dim_*` and `fct_*` tables
4. Build relationships:
   - `fct_boutique_sales.date_key` → `dim_date.date_key`
   - `fct_boutique_sales.client_id` → `dim_customers.client_id`
   - `fct_boutique_sales.sku_id` → `dim_product.sku_id`
   - (repeat for other facts)
5. Key reports to build:
   - **Omnichannel revenue** — boutique + ecom by month, store, product category
   - **VIP concentration** — top 20% clients = X% of revenue
   - **Advisor performance** — revenue and client count per advisor
   - **Inventory scarcity** — reorder flags, days of stock by store/SKU
   - **After-sales** — repair volume, avg turnaround by service type
   - **Wholesale sell-through** — partner comparison, category performance

---

## Daily Schedule Summary

| Time (UTC) | Activity |
|---|---|
| 02:00 | Railway generates yesterday's data → pushes to Supabase / Firebase / Azure Blob |
| 03:00 | Pipeline A: Supabase → Bronze tables |
| 03:30 | Pipeline B: FastAPI → Bronze JSON files |
| 04:00 | Notebook A: Wholesale CSVs → Bronze tables |
| 04:15 | Notebook B: API JSONs → Bronze tables |
| 04:30 | dbt build: Bronze → Silver → Gold |
| 05:30 | Power BI dataset refresh |

---

## Connections & Credentials Reference

| System | Credential | Where used |
|---|---|---|
| Supabase Postgres | `SUPABASE_DB_PASSWORD` + host in `.env` | Pipeline A connection |
| Azure Blob | Account key from Azure portal → Storage → Access keys | Shortcut auth |
| FastAPI | `x-api-key` header — value in `generator/.env` (`API_KEY`) | Pipeline B HTTP header |
| Fabric Lakehouse | Workspace connection string | dbt profiles.yml |

---

## Re-running / Backfilling in Fabric

To reprocess a historical date range:
1. Re-run the orchestration pipeline with a date parameter override
2. Notebooks use `today` variable — override it to target a specific date
3. Bronze tables use `mode("append")` for event data — use `mode("overwrite")` for re-runs to avoid duplicates

For a full historical backfill (first-time setup), run the orchestration pipeline once per date from 2026-01-01 → today using a ForEach activity looping over a date array.
