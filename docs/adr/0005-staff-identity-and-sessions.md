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

Do not trim, lowercase or otherwise silently normalize passwords.

Bound password input size and rate-limit login attempts.
Return a generic authentication failure for invalid credentials.

Password verification must not hold operational database locks.

## Sessions

Generate a new cryptographically random opaque token after successful login.

Store only its SHA-256 digest in the database.
The raw session token is delivered through an HTTP-only cookie.

Each session records its user, creation time, expiry and revocation state.

Enforce expiration on the server.
Use a configurable absolute lifetime, initially eight hours.
Also enforce a configurable idle timeout, initially thirty minutes.

Logout revokes the current session and clears its cookie.
Disabled users and revoked or expired sessions cannot authenticate.

Do not store session tokens in browser localStorage.

## Cookies and transport

Use a host-only session cookie with Path=/ and SameSite=Lax.

Set HttpOnly.
Require Secure cookies and HTTPS in production.

Local HTTP development may use a non-Secure cookie.
Production configuration must reject that setting.

Do not trust client-supplied roles, user IDs or forwarding headers
as authentication evidence.

## CSRF and origins

Allow only explicitly configured browser origins.

Protect login against cross-origin requests.
Require JSON requests and validate the browser origin for login.

For authenticated mutations, require a CSRF token bound to the session
and validate the request origin.

SameSite cookies are additional protection, not a replacement for CSRF checks.

CSRF tokens may be returned to the authorized frontend.
Never expose the session cookie token through an API response.

## Roles and permissions

Initial staff roles are controller and administrator.

Define explicit permission mappings for each supported action.
Administrator access is determined by those mappings, not a blanket bypass.

Permissions cover report review, incident editing/resolution,
timetable management and audit access as those features are implemented.

Derive the actor from the authenticated session.
Recheck authorization in application services used outside HTTP routes.

Role removal and account disabling must affect subsequent requests.

## API

Implement:

- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET /api/v1/auth/me

Responses expose an allowlist of user information and permissions.

Missing or invalid authentication returns 401.
An authenticated actor lacking permission receives 403.
Dependency failures use the existing safe error envelope.

Authentication responses are not cacheable.

## Transaction boundaries

Keep identity queries and mutations separate from future incident
or import transactions.

Do not introduce nested transaction assumptions into the existing
request-scoped database dependency.

Session creation, revocation and relevant identity updates commit explicitly
through their application service.

## Rate limiting

Protect login using bounded per-client and per-account limits.

Do not rely solely on an in-memory limit across multiple workers.
Document and test the selected enforcement mechanism.

Never accept an untrusted forwarded IP as the authoritative client address.

## Frontend

Add a staff login page, session state and permission-aware navigation.

Restore session state through /auth/me.
Keep the session cookie inaccessible to JavaScript.

Attach CSRF protection to authenticated mutations.
Handle session expiry visibly without pretending that a write succeeded.

Frontend route guards are convenience, not authorization boundaries.

## Validation

Cover:

- Correct and incorrect passwords.
- Unknown and disabled users.
- Expired, idle-expired and revoked sessions.
- Logout invalidation.
- Cookie attributes and production configuration.
- Missing and invalid CSRF tokens.
- Disallowed origins.
- Login rate limits.
- Permission denial and role changes.
- No credential or token exposure in public responses.

## Consequences

Database-backed sessions support revocation and individual attribution.

Identity introduces protected state and additional tests, but enables
accountable incident review and management workflows.

Passenger accounts, recovery flows and additional authentication methods
remain later work unless required by the v1 acceptance gates.
