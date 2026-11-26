# Feature: dynamic-pricing

## Objective

Replace the cost-based pricing model inherited from Domu with direct, editable seasonal adjustments, and remove the costs module.

## Problem

Nightly price today is `floor + (base - floor) * profitability%`, where `floor` comes from the costs module. Owners must load costs and reason in "profitability %", which is not how a cabin owner thinks ("January +30%"). Rules cannot overlap and cannot change over PAID bookings.

## Why

The product (Quila) is a white-label booking system for a single cabin business, integrated with the chatv2 bot. The owner needs to adjust prices during the season quickly; the bot quotes with whatever rules are current.

## Scope

- Remove the costs module end to end (models, repo, service, router, schemas, tests, frontend UI, `avg_stay_days`, cost enums).
- Pricing rules: `adjustment_type` (`PERCENTAGE` | `FIXED_PRICE`), `adjustment_value`, `priority`; overlaps allowed.
- Nightly price: `base * (1 + pct/100)` or the fixed price of the winning rule; base = versioned base price for the date, else `Property.base_price`.
- Winning rule for a date: highest `priority`; tie -> most recently created.
- Existing bookings keep their `total_amount` snapshot; editing rules never changes them.
- Financial summary becomes revenue-only (no costs / profit).

## Constraints

- Router -> Service -> Repository; services never commit.
- New Alembic migrations (010+); no production data exists.
- Base price versioning stays.
- Known failing tests on the base commit (not caused by this feature): `test_auth.py::test_register_success`, `test_register_duplicate_email`, `test_register_duplicate_username`, `test_login_success`, `test_bookings.py::test_delete_booking`, `test_costs.py::test_list_costs_shows_only_current_version` (file removed by T2).

## Delivery strategy

`exception-ok`: forecast exceeds ~400 authored lines, but most of it is deletion of the costs module, which is easy to review as one branch. One work-unit commit per task on `feat/dynamic-pricing`.

## Tasks

- [x] T1 Test baseline: add the SQLAlchemy asyncio extra (`greenlet`) to `api/requirements.txt` so the test image imports. Route: delegated (same writer as T2-T5).
  - Evidence: `requirements.txt` now pins `sqlalchemy[asyncio]`; `docker compose -p quila run --rm --no-deps web python -m pytest -q` -> 6 failed, 65 passed (exactly the 6 documented pre-existing failures).
- [x] T2 Remove costs module (backend + migration 010 + revenue-only financial summary). Route: delegated — writer trigger (2+ non-trivial files).
  - Evidence: pytest -> 5 failed, 53 passed (only the 5 documented pre-existing failures; `test_costs.py` removed). Entrypoint `alembic upgrade head` reached `010` on a DB at `009`; `property_costs`, `costcategory`, `costcalculationtype` and `properties.avg_stay_days` gone.
  - Financial summary now returns `total_income`, `paid_income`, `pending_income` (+ occupancy). Income per booking = `paid_amount` if recorded, else the `total_amount` snapshot, prorated by nights inside the month; bookings without a stored total fall back to current nightly prices. Nights are counted up to the first day of the next month (the previous code dropped the month's last night).
- [x] T3 New pricing rule model + formula + migration 011; batch rule lookup (no N+1); booking creation fails loudly if the quote fails instead of storing a null total; drop the "no rule changes over PAID bookings" and "no overlap" restrictions. Test-first. Route: delegated.
  - RED: 22 new/updated tests in `tests/test_pricing.py` failed before implementation (422 on the new payload, old formula totals, booking created with a missing property).
  - GREEN: pytest -> 5 failed, 75 passed (only the 5 documented pre-existing failures).
  - Migrations on a fresh DB: `alembic upgrade head` -> 011; `downgrade -1` twice -> 009; `upgrade head` -> 011. Data round trip of 011 checked by hand (PERCENTAGE -20 -> profitability 80, single-day rule widened to 2 days on downgrade; back up -> PERCENTAGE 0, priority 0).
  - Decisions: rule dates are inclusive and `end_date >= start_date` (DB check relaxed from `>`); validation in `PricingRuleCreate` (422) and, for partial updates, in the service on the merged values (400); explicit nulls in an update mean "unchanged". Calendar no longer returns `floor_price` / `profitability_percent`. `BookingRepository.exists_paid_booking_overlap` removed (no callers left).
- [x] T4 Frontend: remove cost UI, update pricing rule dialogs/table/calendar, revenue-only report, types and messages. Route: delegated.
  - Evidence: `npx tsc --noEmit` -> exit 0, no errors. `npm run lint` -> ESLint cannot load `eslint-config-next/core-web-vitals` (config resolution error, `eslint.config.mjs` untouched; environmental). Backend pytest unchanged: 5 failed (documented), 75 passed. `rg -il "cost|floor_price|avg_stay|profitability" frontend/src frontend/messages` -> no hits.
  - Cost components/actions and the property "Costs" section removed; `avg_stay_days` removed from property forms. New `PricingAdjustmentFields` (type select, value, priority, live estimated price) is shared by the add/edit dialogs and the calendar inline rule form; the rules table shows adjustment and priority. `FinancialReport` and the home dashboard show total / paid / pending income instead of costs and profit.
- [ ] T5 Docs: `AGENTS.md`, `api/AGENTS.md`, `api/API_ENDPOINTS.md`, `frontend/AGENTS.md`. Route: delegated.

## Acceptance criteria

- No cost tables, endpoints, or UI remain; migrations upgrade from an empty DB to head.
- Quote over a range with overlapping rules uses the highest-priority rule per night; PERCENTAGE and FIXED_PRICE both covered by tests.
- Changing a rule does not alter existing bookings' `total_amount`.
- Backend suite passes except the documented pre-existing failures; frontend type-check passes.

## Checks

- Backend: `docker compose -p quila run --rm --no-deps web python -m pytest -q` (isolated compose project; do not touch chatv2 containers on ports 8000/3000).
- Frontend: `npx tsc --noEmit` in `frontend/`.

## Progress

- Branch `feat/dynamic-pricing` created from master `4395eae`.
- T1 committed: `83a534a`.
- T2 committed: `276f26d`.
- T3 committed: `17a7114`.

## Next step

T1-T5 via one delegated writer.
