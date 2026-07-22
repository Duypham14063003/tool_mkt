## ADDED Requirements

### Requirement: Interactive TikTok browser connection
The system SHALL connect a TikTok account through a visible Playwright browser without requiring a TikTok client key, client secret, or OAuth redirect URI. The system MUST allow the operator to complete authentication challenges manually and MUST only mark the account connected after authenticated TikTok Studio access is verified.

#### Scenario: Operator completes TikTok login
- **WHEN** an authenticated dashboard user starts TikTok connection and completes TikTok login in the launched browser before the timeout
- **THEN** the system verifies authenticated TikTok Studio access, stores the discovered account identifier and protected session state, and marks TikTok connected for that dashboard user

#### Scenario: Login requires human verification
- **WHEN** TikTok presents CAPTCHA, two-factor authentication, or another interactive challenge
- **THEN** the system leaves the visible browser available for the operator to complete the challenge and does not attempt to bypass it

#### Scenario: Login is not completed
- **WHEN** the operator closes the browser or the configured connection timeout expires before authenticated Studio access is verified
- **THEN** the system reports that connection was not completed and does not create or replace the user's stored TikTok connection

### Requirement: Protected and isolated browser sessions
The system MUST encrypt persisted TikTok browser session state at rest, MUST associate it with exactly one dashboard user, and MUST NOT expose session cookies or storage values in logs or client responses.

#### Scenario: Session is persisted
- **WHEN** TikTok connection or synchronization succeeds and Playwright returns updated storage state
- **THEN** the system encrypts the complete state before database persistence and replaces only that dashboard user's TikTok session state

#### Scenario: Concurrent users access TikTok analytics
- **WHEN** two dashboard users request TikTok operations
- **THEN** each browser context receives only the session state associated with its requesting dashboard user

#### Scenario: TikTok is disconnected
- **WHEN** a dashboard user confirms TikTok disconnection with a valid CSRF token
- **THEN** the system deletes that user's persisted TikTok session material and no longer treats TikTok as connected

### Requirement: Playwright-based TikTok analytics collection
The system SHALL collect available TikTok Studio content analytics through the authenticated browser session and SHALL NOT use TikTok OAuth or Open API endpoints for TikTok connection, token refresh, or analytics retrieval.

#### Scenario: Analytics collection succeeds
- **WHEN** a connected user requests TikTok statistics and the stored session remains authenticated
- **THEN** the system navigates to TikTok Studio, extracts available content metrics, refreshes rotated session state, and closes all browser resources

#### Scenario: Multiple requests target one connection
- **WHEN** connect or analytics operations overlap for the same TikTok connection
- **THEN** the system serializes session-mutating browser work for that connection and applies bounded timeouts

### Requirement: Normalized TikTok statistics contract
The system SHALL continue serving `GET /api/v1/stats/tiktok` with the normalized structure expected by the dashboard, including platform, summary, daily, content, and fetched-at values. Content items SHALL include an identifier, title, creation time, URL when available, views, engagement, likes, shares, and average watch time using safe defaults for unavailable optional metrics.

#### Scenario: TikTok Studio returns content analytics
- **WHEN** authenticated Studio pages contain valid video analytics rows
- **THEN** the endpoint returns `platform` as `tiktok`, calculated summary totals, daily aggregates, normalized content items, and an ISO-8601 fetch timestamp

#### Scenario: An optional metric is unavailable
- **WHEN** TikTok Studio does not expose an optional metric for the connected account or content type
- **THEN** the normalized item uses a documented safe default without failing the entire response

### Requirement: Actionable browser collection failures
The system SHALL distinguish an expired authentication session, unavailable analytics, incompatible TikTok page layout, and browser runtime failure without disclosing sensitive browser state.

#### Scenario: Stored session has expired
- **WHEN** a statistics request is redirected to TikTok login or otherwise fails the authenticated-session check
- **THEN** the endpoint reports that TikTok must be reconnected and does not overwrite the last valid stored session with an unauthenticated state

#### Scenario: TikTok layout cannot be parsed
- **WHEN** required Studio elements or fields cannot be located or validated
- **THEN** the endpoint returns a controlled upstream error identifying a TikTok layout incompatibility and logs only non-sensitive diagnostic context

#### Scenario: Browser runtime is unavailable
- **WHEN** Chromium cannot launch or the configured browser operation times out
- **THEN** the system returns an actionable browser-runtime error and closes any partially created resources

### Requirement: Facebook integration remains independent
The system MUST leave Facebook OAuth, stored Facebook credentials, Graph API collection, and normalized Facebook statistics behavior unchanged when TikTok switches to Playwright.

#### Scenario: Facebook and TikTok are both connected
- **WHEN** the dashboard loads analytics for both platforms
- **THEN** Facebook data is collected through the existing Graph API flow while TikTok data is collected through Playwright and both retain their existing normalized dashboard contracts
