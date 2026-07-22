## 1. Browser Runtime and Configuration

- [ ] 1.1 Add the Python Playwright dependency and document/install the supported Chromium runtime.
- [ ] 1.2 Replace TikTok OAuth environment settings with browser enablement, executable/launch options, connect timeout, and navigation timeout configuration.
- [ ] 1.3 Generalize encrypted provider-credential helpers and error wording so `SocialAccount` can safely store Playwright storage-state JSON without exposing it.

## 2. TikTok Browser Session Service

- [ ] 2.1 Replace the TikTok Open API client with Playwright browser/context lifecycle helpers that always enforce timeouts and close resources.
- [ ] 2.2 Implement headed interactive connection, authenticated TikTok Studio detection, account identifier discovery, and storage-state capture without automating credentials or verification challenges.
- [ ] 2.3 Implement per-account operation locking and safe encrypted storage-state load, refresh, and preservation behavior.
- [ ] 2.4 Implement headless TikTok Studio navigation, centralized selectors, numeric/date parsing, pagination or bounded content collection, and normalized metric aggregation.
- [ ] 2.5 Add typed handling for reauthentication, unavailable analytics, incompatible layout, launch failure, and timeout conditions with non-sensitive diagnostics.

## 3. Flask and Dashboard Integration

- [ ] 3.1 Replace TikTok OAuth start/callback routes with the interactive Playwright connection flow and only persist a connection after verified authentication.
- [ ] 3.2 Preserve `GET /api/v1/stats/tiktok` while mapping Playwright service failures to actionable sanitized responses.
- [ ] 3.3 Update TikTok disconnect behavior to remove all persisted browser session material and update connection UI copy for interactive browser login/reconnection.
- [ ] 3.4 Remove TikTok API credential and callback references from `.env.example` and README while leaving Facebook OAuth documentation and behavior unchanged.
- [ ] 3.5 Define and document migration behavior that invalidates existing TikTok OAuth-token records and requires interactive reconnection.

## 4. Verification

- [ ] 4.1 Add unit tests for storage-state encryption/isolation, metric parsing and normalization, selector failures, expired sessions, and safe optional-metric defaults using mocked Playwright objects or sanitized fixtures.
- [ ] 4.2 Add route tests for successful/cancelled/timed-out connection, session persistence, statistics errors, CSRF-protected disconnect, and absence of TikTok developer credentials.
- [ ] 4.3 Add concurrency and cleanup tests proving same-account operations serialize and browser resources close after success, timeout, and exceptions.
- [ ] 4.4 Run the full automated test suite and manually verify headed TikTok login, headless analytics refresh, reconnect, disconnect, and unchanged Facebook connection/statistics flows with authorized test accounts.
