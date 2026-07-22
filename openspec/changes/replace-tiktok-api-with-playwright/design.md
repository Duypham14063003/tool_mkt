## Context

The Flask application currently redirects users through TikTok OAuth, stores encrypted access and refresh tokens in `SocialAccount`, and calls TikTok Open API from `TikTokService` each time the dashboard requests `/api/v1/stats/tiktok`. This makes TikTok analytics dependent on developer-app credentials and API approval. The replacement must preserve the normalized response consumed by `static/js/dashboard.js`, isolate browser credentials between local dashboard users, and account for interactive authentication challenges and an unstable third-party UI.

The first version targets an operator-controlled environment where the Flask host can launch a visible browser for connection. Background analytics reads can use a headless browser after the session is established.

## Goals / Non-Goals

**Goals:**

- Connect TikTok without TikTok developer credentials or OAuth callbacks.
- Let the operator complete login, CAPTCHA, and two-factor authentication in a visible browser.
- Encrypt persisted Playwright session state and isolate it by dashboard user.
- Scrape TikTok Studio analytics and preserve the existing normalized TikTok stats contract.
- Return actionable errors when authentication expires, analytics are unavailable, or the UI can no longer be parsed.
- Leave the Facebook integration unchanged.

**Non-Goals:**

- Automating CAPTCHA, two-factor authentication, or password entry.
- Obtaining TikTok developer credentials or calling private/undocumented TikTok APIs directly.
- Guaranteeing unattended connection on a headless server with no operator-accessible display.
- Evading TikTok anti-automation controls.
- Supporting multiple TikTok accounts for one dashboard user in this change.

## Decisions

### Use Playwright for Python with separate connect and sync modes

The connect route launches Chromium in headed mode and waits for the operator to complete authentication within a configured timeout. It only marks the account connected after TikTok Studio is reachable as an authenticated user. Subsequent stats requests launch a fresh headless context seeded with the stored session state.

This avoids storing TikTok passwords and permits human handling of CAPTCHA and two-factor authentication. Reusing a permanently running browser was rejected because it is harder to isolate per user, recover after crashes, and operate across multiple Gunicorn workers.

### Persist encrypted Playwright storage state in the existing account record

The Playwright `storage_state` JSON is stored through the existing encrypted `SocialAccount.access_token` field; the service treats it as opaque browser-session material rather than an OAuth token. `platform_user_id` stores the account identifier discovered after login. Session state is refreshed after successful browser operations when TikTok rotates cookies.

This minimizes schema changes and reuses the established Fernet protection. Storing a plaintext Playwright profile directory was rejected because it exposes cookies on disk and complicates per-user cleanup. Implementation naming and error messages will be generalized from “OAuth token” where needed so the model accurately represents encrypted provider credentials.

### Preserve the internal normalized stats endpoint

`GET /api/v1/stats/tiktok` remains the browser-facing endpoint and returns the existing `platform`, `summary`, `daily`, `content`, and `fetched_at` structure. `TikTokService` becomes a Playwright-backed adapter that extracts rows from TikTok Studio and normalizes missing values to safe defaults.

Preserving the endpoint avoids unnecessary dashboard JavaScript changes. Introducing a new API version was rejected because the consumer-facing payload does not need to change.

### Prefer observable UI state and centralized selectors

Authentication checks, navigation, and analytics extraction use visible page state. Selectors and parsing helpers are centralized in the TikTok service, prefer stable accessible labels or table structure, and include narrowly scoped fallbacks. The scraper validates required fields before returning data and raises typed errors for `reauthentication_required`, `analytics_unavailable`, `layout_changed`, and browser/runtime failures.

This does not attempt to call endpoints observed in browser traffic because doing so would recreate an undocumented API dependency and could bypass intended browser behavior.

### Serialize browser work per TikTok connection

Only one connect or sync operation may mutate a given user's TikTok session at a time. An application-level keyed lock is sufficient for the initial single-host deployment; the service uses bounded navigation and operation timeouts and always closes contexts and browsers in `finally` blocks.

For a multi-host deployment, the keyed lock must be replaced by a distributed lock or the TikTok browser worker must be separated into a single-consumer job service. Unbounded concurrent browser launches were rejected due to resource and session-corruption risks.

### Make browser requirements explicit configuration

TikTok client key, secret, and redirect URI are removed. Configuration adds browser executable/launch options, connect timeout, navigation timeout, and a feature switch that can disable browser automation when the runtime is unavailable. Production startup documentation includes `playwright install chromium` and the need for a display mechanism during interactive connection.

## Risks / Trade-offs

- [TikTok changes Studio markup or labels] → Centralize selectors, validate parsed records, return `layout_changed`, and cover parsers with saved sanitized fixtures where feasible.
- [TikTok detects or blocks automated browsing] → Use standard Playwright behavior, bounded request frequency, no CAPTCHA bypass, and surface the failure for manual action.
- [Session cookies grant account access] → Encrypt state at rest, never log it, isolate it per user, use temporary contexts, and delete it on disconnect.
- [Headed login is unavailable in production] → Document the operator/display requirement and fail connection with a clear runtime error rather than accepting a partial account.
- [Browser launches increase latency and memory] → Serialize per account, enforce timeouts and limits, and close all resources deterministically; background caching is deferred.
- [Existing `access_token` naming becomes misleading] → Keep the column for migration simplicity but generalize model/service APIs and documentation around encrypted credentials.
- [Terms or platform policy may restrict automated collection] → Require the deployer to confirm authorization and TikTok terms; do not add stealth or anti-detection measures.

## Migration Plan

1. Add Playwright, install Chromium, and add browser runtime configuration while retaining the old TikTok code behind the current implementation until tests pass.
2. Replace TikTok service and routes, update connection messaging, and remove TikTok OAuth configuration from `.env.example` and documentation.
3. Invalidate existing TikTok OAuth-backed `SocialAccount` records because their encrypted token payload cannot be interpreted as Playwright state; require those users to reconnect interactively.
4. Deploy only where a headed connection browser is available, then verify connect, sync, expired-session, disconnect, and Facebook regression paths.
5. Roll back by restoring the prior service/routes/configuration and requiring TikTok users to reconnect through OAuth; browser session JSON is not convertible to OAuth tokens.

## Open Questions

- Whether a future production deployment needs a separate browser worker and distributed lock depends on its host count and expected concurrent TikTok users.
- Exact TikTok Studio selectors and the metrics available to each account type must be confirmed during implementation against an authorized test account.
