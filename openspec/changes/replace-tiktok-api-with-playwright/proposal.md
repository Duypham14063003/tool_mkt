## Why

The dashboard currently requires a registered TikTok developer application and approved API access before it can connect an account or display analytics. Replacing that integration with an operator-controlled Playwright browser session allows the dashboard to collect TikTok Studio analytics without `TIKTOK_CLIENT_KEY` or `TIKTOK_CLIENT_SECRET`.

## What Changes

- Add an interactive TikTok browser connection flow in which the operator completes login, CAPTCHA, and two-factor authentication when required.
- Persist the authenticated Playwright session securely and reuse it for later analytics synchronization.
- Collect TikTok content and summary metrics from TikTok Studio and normalize them into the dashboard's existing stats response shape.
- Detect expired sessions, unavailable analytics, and TikTok page-layout changes and report actionable connection or synchronization errors.
- Keep the existing Facebook OAuth and Graph API integration unchanged.
- **BREAKING**: Remove TikTok OAuth callback behavior and the requirement for `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, and `TIKTOK_REDIRECT_URI`; TikTok connection now requires a browser-capable runtime and an interactive first login.

## Capabilities

### New Capabilities

- `tiktok-browser-analytics`: Connect a TikTok account through an interactive Playwright session, securely retain that session, and collect normalized TikTok analytics without the TikTok developer API.

### Modified Capabilities

None.

## Impact

- Affects TikTok routes in `app.py`, `services/tiktok_service.py`, TikTok connection state storage, dashboard connection messaging, configuration, deployment documentation, and automated tests.
- Adds Playwright and a supported browser runtime as application dependencies.
- Removes runtime calls to TikTok OAuth and Open API endpoints while preserving `GET /api/v1/stats/tiktok` as the dashboard-facing normalized endpoint.
- Introduces operational sensitivity to TikTok Studio UI changes and requires secure storage and cleanup of browser session state.
