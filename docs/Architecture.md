# Architecture

This implementation uses a dependency-free Python 3 WSGI backend and a static French HTML/CSS/JavaScript single-page interface. This is a pragmatic runnable stack in the supplied workspace, which contained no existing source repository and had Python 3.13/Node but no PHP or Composer. The previous workspace project consisted of specification-derived documents and templates only; there was no app to preserve and no Git repository.

## Components and trust boundaries
- Browser: renders static UI; sends same-origin JSON requests; never holds GLPI or AI keys.
- WSGI application (`app.py`): routing, validation, signed session handling, authorization checks, service calls, response headers.
- SQLite: local application accounts, minimal audit log, and seven provisional entity-code mappings (no item quantities or stock movements). GLPI remains source of truth for tickets and, once a compatible module is verified, must remain the source of truth for stock too.
- GLPI REST client: server-to-server HTTPS calls using configured app/user tokens; request timeout and sanitized failure messages.
- AI client: compatible `/chat/completions` server-side HTTP call; system instruction treats supplied text as untrusted; no tool calling implemented in this version.

## Data flow
Login/setup → PBKDF2 password verification → signed expiring HttpOnly cookie. Authorized ticket requests use backend client to call GLPI and return API data. Assistant requests go to configured AI endpoint. Health check reports application/DB status and integration configuration state separately. No conversation data is persisted.

## Security decisions and boundaries
- No dependency or build system; Python standard library only.
- Passwords stored as salted PBKDF2-HMAC-SHA256 (310,000 iterations); signed cookie; SameSite Strict; Secure cookie when `APP_ENV=production`.
- Mutating requests with an Origin header must match the request Host; SameSite Strict cookie is also used. This is a basic CSRF mitigation, not a substitute for a synchronizer token under all proxy/browser topologies.
- Body size bound; basic length validation; HTML output escapes ticket values with `textContent`/escaping.
- GLPI/AI endpoints and secrets exist only server-side. Non-HTTPS remote endpoints are rejected.
- This is a local/dev reference implementation, not production hardened: rate limits are process-memory only; no MFA/SSO, structured external logging, session revocation/rotation or admin user edit/delete UI; built-in server is development-only; Origin checks depend on correct reverse-proxy Host handling; no real GLPI contract test. Do not expose publicly until these items are reviewed and target GLPI release is tested.
