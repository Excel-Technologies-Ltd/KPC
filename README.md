# KPC Operations

An end-to-end Petroleum Operations Platform for Kenya Pipeline Company (KPC) — built on [Frappe](https://frappeframework.com) and integrated with standard [ERPNext](https://erpnext.com) Accounts.

It tracks physical petroleum cargo from vessel arrival through to financial posting, across 13 steps, with an integrated AI predictive-maintenance event during pipeline movement. A single **Golden Thread** ID (`journey_ref`) is enforced on every transaction in the chain, so any cargo can be traced end to end.

## The Golden Thread

Every transaction doctype in this app carries a mandatory `journey_ref` — a `Link` to a **Journey** record, not a free-text string. `Journey` is the golden-thread master: it's created automatically the moment an `Oil Shipment` is first saved, and every subsequent step appends an audit row to its `journey_log` child table via one shared helper:

```python
from kpc.petroleum_operations.utils import log_journey_step

log_journey_step(self.journey_ref, "7. Movement", self)
```

A `Journey` is read-only and system-maintained — nobody edits it by hand. Open any `Journey` record to see the complete, ordered history of every document raised against that cargo, from the originating `Oil Shipment` all the way to the `Financial Posting` that closed it out.

## The 13-Step Workflow

| # | Step | DocType(s) |
|---|------|-----------|
| 1 | Shipment | `Oil Shipment` |
| 2 | Receipt | `Tank Measurement` |
| 3 | Quality Result | `Quality Result` |
| 4 | Inventory Position | `Inventory Position` |
| 5 | Nomination | `Nomination` |
| 6 | Batch | `Pipeline Batch` |
| 7 | Movement (+ AI) | `Movement`, `AI Alert`, `AI Prediction`, `AI Recommendation`, `Maintenance Work Order` |
| 8 | Terminal Receipt | `Terminal Receipt` |
| 9 | Reconciliation | `Reconciliation`, `Variance` |
| 10 | Allocation | `Allocation` |
| 11 | Dispatch | `Dispatch` |
| 12 | Invoice | `Invoice` (creates a real ERPNext `Sales Invoice`) |
| 13 | Financial Posting | `Financial Posting` (system-generated, mirrors the Sales Invoice's GL posting) |

Supporting masters that aren't part of the numbered sequence: `Terminal`, `Oil Tank`, `Capacity Assessment`, `Tariff`, plus **Product**, which is not a separate doctype — it's the standard ERPNext `Item` extended with petroleum-specific custom fields (`density_at_15c`, `reference_temperature_c`, `api_gravity`, `is_petroleum_product`).

## Architecture Notes

- **Module:** everything lives under the `Petroleum Operations` module (`kpc/petroleum_operations/`), separate from the app's default `Kpc` module.
- **Volumetrics:** `kpc.petroleum_operations.utils.calculate_standard_volume()` converts a tank dip reading to a standard volume at 15°C (linear strapping approximation × a simplified API MPMS 11.1 / ASTM D1250 Volume Correction Factor). Shared by `Tank Measurement` and `Terminal Receipt` so both stay on the same formula. **Not certified for fiscal custody transfer** — replace with a vendor-certified VCF table before relying on it for billing-grade accuracy.
- **AI predictive maintenance:** `kpc.petroleum_operations.utils.assess_pipeline_anomaly()` scores a `Movement`'s telemetry (pressure, flow rate, vibration) against a documented safe-operating envelope — deterministic and explainable by design, not a trained model. A breach cascades automatically: `AI Alert` → `AI Prediction` (failure risk % + horizon) → a draft `AI Recommendation`, which sits in `Pending Approval` until a Maintenance Manager acts.
- **Accounts integration:** `kpc.petroleum_operations.integrations.accounts` is deliberately thin. `Invoice` never writes a GL Entry itself — submitting it builds and submits a real ERPNext `Sales Invoice`, and a `journey_ref` custom field (added to both `Sales Invoice` and `GL Entry`) rides along, stamped onto the GL Entries by a `doc_events` hook *after* ERPNext has already posted them.
- **Native units:** every quantity in this app is kilolitres (KL), end to end. `Invoice` requires a billed product's `stock_uom` to literally be `Kilolitre` and throws rather than guessing a unit-conversion factor.
- **Two ERPNext naming collisions, deliberately avoided:**
  - `Batch` (ERPNext's manufacturing/stock lot doctype) → this app's pipeline parcel is **`Pipeline Batch`**.
  - `Work Order` (ERPNext's manufacturing doctype) → this app's maintenance job is **`Maintenance Work Order`**.

## Roles & Workflows

| Role | Scope |
|------|-------|
| Terminal Operator | Oil Shipment, Tank Measurement, Terminal Receipt, Dispatch |
| Quality Analyst / Quality Manager | Quality Result entry and approval |
| Scheduler & Operations Controller | Capacity Assessment, Pipeline Batch approval, Movement tracking, Variance approval |
| Commercial Officer | Nomination, Allocation, Invoice |
| Maintenance Manager | Exclusive approver of AI Recommendation and Maintenance Work Order |
| Finance Officer | Reconciliation, Invoice (billing), Financial Posting |

Four Frappe Workflows enforce the state machines that need more than one role:

| Workflow | States |
|----------|--------|
| Oil Shipment Workflow | Draft → Vessel Arrived → Discharging → Received (+ Cancel) |
| Quality Result Workflow | Pending → Accepted / Quarantined |
| AI Recommendation Workflow | Pending Approval → Approved / Rejected |
| Variance Workflow | Pending Approval → Approved / Rejected |

Everything else that needs an approval gate (Nomination, Pipeline Batch, Tank Measurement, Terminal Receipt, Reconciliation, Allocation, Dispatch, Invoice, Maintenance Work Order) uses a plain Frappe submit, with submit permission restricted to the owning role.

## Installation

```bash
bench get-app kpc <repo-url>   # or: already present under apps/kpc in this bench
bench --site <site> install-app kpc
bench --site <site> migrate
```

`bench migrate` runs the app's patches (`kpc/patches.txt`), which create the RBAC roles, the `Item`/`Sales Invoice`/`GL Entry` custom fields, the `Kilolitre` UOM, the four Workflows, and the `KPC` Workspace — all idempotent and safe to re-run.

## Demo Data

`kpc/demo_data.py` seeds one complete Golden Thread through all 13 steps, deliberately routed through every control the app enforces — not a synthetic fixture, real records created via the same `insert()`/`submit()` calls a user would trigger from the UI:

```bash
bench --site <site> execute kpc.demo_data.create_demo_data
```

It creates two Terminals, two Oil Tanks, one petroleum Product, one Customer, and then walks a single cargo (`MT African Pride`) through:

- **Step 1–4:** Shipment → Tank Measurement → Quality Result (Accepted) → Inventory Position
- **Step 5–6:** Nomination → Capacity Assessment → Pipeline Batch
- **Step 7:** Movement with a deliberate telemetry breach (overpressure + high vibration) → full AI Alert → AI Prediction → AI Recommendation (Approved) → Maintenance Work Order (Completed) cascade
- **Step 8:** Terminal Receipt
- **Step 9:** Reconciliation outside the default 0.5% tolerance, justified and accepted, then classified and approved as a Variance
- **Step 10–11:** Allocation → two Dispatches (so Invoicing has more than one line to prove itself against)
- **Step 12–13:** Invoice (two rated lines) → a real ERPNext Sales Invoice → two balanced GL Entries, both carrying `journey_ref` → Financial Posting

The script is idempotent (keyed on the demo vessel's name, not autoname counters) — safe to run again; it will find the existing Journey and return without creating duplicates.

Once seeded, open the result at `/app/journey/JNY-2026-00001`, or start from the **KPC** workspace in Desk, which groups every doctype into cards by phase with quick-access shortcuts to the most-used entry points.

## Known Simplifications

- **One `journey_ref` per cargo, start to finish.** Assumes segregated batch tracking (a shipment's product stays traceable as itself through to invoice); real operations sometimes commingle stock from multiple cargoes in one tank.
- **VCF is illustrative, not certified** — see Architecture Notes above.
- **AI scoring is rule-based, not a trained model** — explainable by design, and the documented integration point for a real one.
- **Tariffs are a flat rate per KL** — no tiered pricing, minimum volumes, or contract-specific overrides.

## License

MIT
