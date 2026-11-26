# Feature: bot-contract

## Objective

Expose the HTTP contract the chatv2 chatbot needs to sell cabin stays: catalog for RAG, availability + quote, and holds that a human converts into confirmed bookings.

## Problem

Quila only has user-JWT endpoints, per-property calendars, no capacity data, no hold expiry, and guests require a document number. The bot cannot search availability, cannot authenticate machine-to-machine, and cannot leave a lead for a human to close.

## Why

The client sells cabin stays through a chatbot that answers and pre-reserves, and a human who closes the sale (payment, confirmation).

## Integration facts (chatv2 side, verified)

- chatv2 calls every tool with `POST <endpoint_url>` and a JSON body of the tool arguments, header `Authorization: <auth_header>`, 10 s timeout (`chatv2/backend/app/services/tools/dispatcher.py`).
- On a non-2xx response the bot only sees `Tool returned HTTP <code>`, losing the reason. Expected business outcomes must therefore be HTTP 200 with a structured body.
- chatv2 ingests URLs with an unauthenticated `GET` (httpx + BeautifulSoup), so the catalog export must be public.

## Scope

- Property catalog fields: `max_guests`, `amenities` (list of strings), `check_in_time`, `check_out_time`, `cancellation_policy`, `house_rules`.
- Public catalog export (`GET /public/catalog`, plain text/markdown, active properties only).
- Bot auth: `Authorization: Bearer <BOT_API_KEY>` (env), constant-time comparison, only on `/bot/*`. Missing env key -> bot endpoints disabled (401/503), never open.
- `POST /bot/availability` {check_in, check_out, guests} -> available active cabins with capacity >= guests and their quote.
- `POST /bot/quote` {property_id, check_in, check_out, guests}.
- `POST /bot/holds` {property_id, check_in, check_out, guests, lead_name, lead_phone, lead_email?, notes?} -> TENTATIVE booking, `source=CHATBOT`, `expires_at = now + HOLD_TTL_HOURS` (default 24, env-configurable), quote snapshot.
- Lazy hold expiry: stale TENTATIVE holds (`expires_at < now`) become CANCELLED before availability, calendar, quote, hold and booking create/update conflict checks. No scheduler.
- Panel: the human sees chatbot holds with lead data and expiry; accepting a hold clears `expires_at`.

## Out of scope (deferred)

- Webhook "hold created": chatv2 already learns about the hold from the `create_hold` tool result, so it can trigger its handoff itself. Webhooks for later events (hold confirmed/expired) are a separate feature.
- Periodic expiry sweep (lazy expiry covers correctness).

## Constraints

- Router -> Service -> Repository; services never commit.
- New Alembic migrations (012+).
- The `EXCLUDE` overlap constraint stays the source of truth for double-booking.
- Bot endpoints: HTTP 200 with `{"ok": false, "reason": "<code>", "message": "<es text>"}` for business outcomes (unavailable, over capacity, past dates, unknown or inactive cabin); 401 for auth; 422 only for malformed input.
- Known pre-existing backend failures: `test_register_success`, `test_register_duplicate_email`, `test_register_duplicate_username`, `test_login_success`, `test_delete_booking`.

## Delivery strategy

`ask-on-risk` (default). Forecast is about 700-900 authored lines across tasks. Slice at the first commit that exceeds about 400 lines after asking the chain strategy once.

## Tasks

- [x] T1 Catalog fields on Property (model, migration 012, schemas, panel forms) and public catalog export. Route: delegated. Evidence: pytest 87 passed / 5 known failures (new `test_public_catalog.py` + catalog field tests in `test_properties.py`); `tsc --noEmit` clean; lint 0 errors (3 pre-existing warnings); `npm run build` ok.
- [x] T2 Bot auth dependency (`BOT_API_KEY`) and `/bot` router skeleton with the structured-outcome convention. Route: delegated. Evidence: pytest 95 passed / 5 known failures (`test_bot_auth.py`: valid key, missing key, wrong keys, user JWT, env unset -> 503).
- [x] T3 Availability + quote bot endpoints with lazy hold expiry in the repository. Test-first. Route: delegated. Evidence: RED 16 failed in `test_bot_availability.py` (404, endpoints missing); GREEN full suite 111 passed / 5 known failures. Deviation: lazy expiry needs `Booking.expires_at`, which arrives with migration 013, so the expiry method, its call sites and the expired-hold availability test moved to T4 (migration 013 stays a single revision).
- [x] T4 Holds: booking fields (`expires_at`, `guests`, `lead_name`, `lead_phone`, `lead_email`), `BookingSource.CHATBOT`, `HOLD_TTL_HOURS`, migration 013, `POST /bot/holds`, accept clears expiry; panel shows lead data and expiry. Test-first. Route: delegated. Also carries the lazy expiry moved from T3 (`BookingRepository.expire_stale_holds`, called by bot availability/quote/hold, booking create/update/accept and the calendar). Evidence: RED 22 failed in `test_bot_holds.py`; GREEN full suite 133 passed / 5 known failures; migrations on a fresh DB: upgrade head -> downgrade -1 x2 -> upgrade head ok (`013 (head)`, CHATBOT in `bookingsource`); `tsc --noEmit` clean, lint 0 errors (3 pre-existing warnings), `npm run build` ok. Decisions: hold insert runs in a SAVEPOINT so an EXCLUDE violation returns `unavailable` without poisoning the request transaction (test DB now gets the same EXCLUDE constraint in `conftest.py`); accept sweeps first so an expired hold cannot be accepted; pay and a PUT to CONFIRMED/PAID also clear `expires_at`; the panel also shows an unswept TENTATIVE hold past its expiry as "Vencido".
- [x] T5 Docs (`AGENTS.md`, `api/API_ENDPOINTS.md`, `.env.example`) including the tool JSON Schemas to register in chatv2. Route: delegated. Evidence: tool JSON block in `api/API_ENDPOINTS.md` parses (3 tools, chatv2 `ToolCreate` keys: name, description, parameters_schema, endpoint_url, auth_header); `api/AGENTS.md`, `frontend/AGENTS.md`, root `AGENTS.md` and `.env.example` updated; final pytest 133 passed / 5 known failures.

## Acceptance criteria

- Without a valid bot key, `/bot/*` returns 401; with `BOT_API_KEY` unset, the bot endpoints are not usable.
- Availability excludes cabins that are booked (including live holds), inactive, or too small, and includes cabins whose only blocker is an expired hold.
- A hold blocks the dates until it expires or is cancelled; after expiry the same dates can be held again.
- Business failures reach the bot as HTTP 200 with a reason code and a Spanish message.
- Backend suite passes except the known failures; frontend `tsc`, lint and build pass.

## Checks

- Backend: `docker compose -p quila run --rm --no-deps web python -m pytest -q` (isolated; chatv2 holds ports 8000/3000).
- Frontend: `npx tsc --noEmit`, `npm run lint`, `npm run build` in `frontend/`.

## Progress

- Branch `feat/bot-contract` created from master `0147ca1`.
- T1 committed `76005f4`.
- T2 committed `cbb6b4c`.
- T3 committed `2548aa4`.
- T4 committed `1e9a9ab`.
- T5 docs committed (see `git log`); all tasks done.

## Next step

Parent: delivery slicing (branch exceeds about 400 authored lines), native review, push/PR. Follow-up (pre-existing, out of scope): `PricingService.get_calendar` checks conflicts with an exclusive `end_date` while it prices `end_date` inclusive, so a booking starting on the last calendar day shows AVAILABLE.
