# ADR 0005: Staff identity and sessions

## Status

Accepted

## Context

The v1 handbook requires individual staff identities, explicit permissions,
expiring and revocable sessions, and attributable review decisions.

Public journey searches remain available without staff authentication.
Protected management actions must enforce authorization on the backend.

## Decision

Implement identity as a separate module within the existing backend.

Use individual staff accounts, database-backed role assignments and
explicit permission checks.

Initial provisioning uses an interactive command.
Do not include default passwords or public administrator credentials.

Public staff registration is outside the pilot scope.

## Passwords

Hash passwords using Argon2id through argon2-cffi.

Store only encoded password hashes.
Verify using the library and upgrade outdated hashes after successful login.

Provisioned passwords must contain 15 to 128 characters.
Do not trim, lowercase or otherwise silently normalize passwords.

Bound password input size and rate-limit login attempts.
Return a generic authentication failure for invalid credentials.

Password verification must not hold operational database locks.

Provisioning rejects existing usernames rather than changing their
passwords or roles.

## Sessions

Generate a new cryptographically random opaque token after successful login.

Store only its SHA-256 digest in the database.
Deliver the raw session token through an HTTP-only cookie.

Each session records its user, account authentication version,
creation time, last activity, absolute expiry and revocation state.

Enforce expiration on the server.
Use a configurable absolute lifetime, initially eight hours.
Also enforce a configurable idle timeout, initially thirty minutes.

Logout revokes the current session and clears its cookie.

Disabled users, changed account authentication versions, and revoked
or expired sessions cannot authenticate.

Do not store session tokens in browser localStorage.

## Cookies and transport

Use a host-only session cookie with Path=/ and SameSite=Lax.

Set HttpOnly.
Require Secure cookies and HTTPS in production.

Local HTTP development may use a non-Secure cookie.
Production configuration must reject that setting.

Do not trust client-supplied roles, user IDs or forwarding headers
as authentication evidence.

Deployment must configure trusted proxies correctly.

## CSRF and origins

Allow only explicitly configured browser origins.

Protect login against cross-origin requests.
Require JSON requests and validate the browser origin for login.

For authenticated mutations, require a CSRF token bound to the session
and validate the request origin.

SameSite cookies supplement origin and CSRF checks.

CSRF tokens may be returned to the authorized frontend.
Never expose the session cookie token through an API response.

## Roles and permissions

Initial staff roles are controller and administrator.

Define explicit permission mappings for each supported action.
Administrator access is determined by those mappings.

Controller permissions are:

- reports.read
- reports.review
- incidents.edit
- incidents.resolve

Administrator permissions additionally include:

- timetable.manage
- audit.read

Unknown roles grant no permissions.

Derive the actor from the authenticated session.
Recheck authorization in application services used outside HTTP routes.

Role removal and account disabling must affect subsequent requests.

Permission-specific report, incident, import and audit workflows are
implemented in subsequent feature branches.

## API

Implement:

- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET /api/v1/auth/me

Responses expose an allowlist of user information and permissions,
the session CSRF token and absolute expiry.

Missing or invalid authentication returns 401.
An authenticated actor lacking permission receives 403.
Unsupported login content types receive 415.
Rate-limited login attempts receive 429 with Retry-After.

Dependency failures use the existing safe error envelope.

Session responses use cache prevention headers.
The frontend also disables caching for API requests.

## Transaction boundaries

Keep identity queries and mutations separate from future incident
or import transactions.

Use a dedicated identity database dependency.
Do not introduce nested transaction assumptions into the existing
request-scoped business database dependency.

Provisioning and session services require caller-owned transactions.
The login workflow manages explicit transactions on a fresh session.

Commit login-limit counters before rejecting credentials.
Perform password verification outside operational database locks.

Before session creation, lock and recheck the account and credential state.
Reject a login if that state changed during password verification.

## Rate limiting

Protect login using bounded per-client and per-account limits.

Persist counters in PostgreSQL and update them atomically.
Do not rely solely on an in-memory limit across multiple workers.

Default limits are 30 attempts per client and 5 per account
within a five-minute window.

Rejected attempts remain counted within the current window.

Never accept an untrusted forwarded IP as the authoritative client address.

Verify client and account admission limits through concurrent attempts
using independent database connections.

## Identity-record cleanup

Provide an operator-run command to preview and remove old identity records.

Preview is the default and performs no writes.
Deletion requires an explicit --apply option.

By default, retain expired or revoked sessions for seven days after their
expiry or revocation, and expired login-limit records for one day after
their window ends.

Use bounded batches, initially 500 records per table and at most 1000.
Lock deletion candidates and skip records locked by another transaction.

Cleanup must preserve current sessions, current rate-limit windows,
users and role assignments.

Applied deletion is transactional.

Session expiry and revocation are enforced during authentication,
independently of whether cleanup has run.

Deployment must arrange an operator procedure or scheduled job.
The application does not automatically schedule cleanup.

## Frontend

Provide public journey-search navigation and a separate staff-access section.

Restore session state through /auth/me.
Keep the session cookie inaccessible to JavaScript.

Support login, logout and explicit session refresh.
Display account roles, permissions and absolute expiry.

Clear password input after submission.
Keep session and CSRF state out of browser localStorage.

Attach CSRF protection to authenticated mutations.

Display session expiry visibly.
Explain that idle expiry may occur before absolute expiry.

Failed logout must not be presented as a confirmed sign-out.
Abort outstanding requests when the staff panel unmounts.
Ignore responses belonging to cancelled or superseded requests.

Frontend navigation and permission displays are convenience features.
Every protected management action still requires backend authorization.

Displaying permissions does not implement the corresponding
incident, import or audit workflows.

## Validation

Cover:

- Correct and incorrect passwords.
- Unknown and disabled users.
- Provisioning and duplicate usernames.
- Expired, idle-expired and revoked sessions.
- Account authentication-version changes.
- Logout invalidation and cookie replay.
- Cookie attributes and production configuration.
- Missing and invalid CSRF tokens.
- Disallowed origins and unsupported content types.
- Login rate limits and concurrent admission.
- Permission denial and role changes.
- No password hashes or raw session tokens in public responses.
- Cleanup retention, preservation, batch limits and rollback.
- Frontend restoration, login, logout and expiry.
- Password-field clearing.
- Unconfirmed logout handling.
- HTTP cookie, CSRF and error-response handling.
- Navigation between public journeys and staff access.
- Cancellation when the staff panel unmounts.

## Consequences

Database-backed sessions support revocation and individual attribution.

Identity introduces protected state and additional tests, but enables
accountable incident review and management workflows.

Cleanup requires an operational procedure or deployment schedule.

Passenger accounts, recovery flows and additional authentication methods
remain later work unless required by the v1 acceptance gates.
