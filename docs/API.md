# HTTP API (implemented routes)
Base path `/api`. JSON request/response unless noted. Authentication uses an 8-hour signed HttpOnly cookie; no API secret is exposed to browser code. All endpoints are same-origin. Session cookie uses `SameSite=Strict`; production must use HTTPS and set Secure cookie (see deployment limitations).

| Method & path | Auth | Behavior |
|---|---|---|
| GET `/api/health` | No | Reports application/database and whether GLPI/AI are configured; stock always reports `not_configured` until a compatible module is integrated; never returns secret values |
| POST `/api/auth/setup` | No, one time | Creates the initial admin only when `ALLOW_ADMIN_SETUP=true` and user table is empty; body `{username,password}`; 12+ char password |
| POST `/api/auth/login` | No | Body `{username,password}`; sets signed session cookie |
| POST `/api/auth/logout` | Session optional | Clears session cookie |
| GET `/api/auth/me` | Session | Current app identity and role |
| GET `/api/glpi/health` | Session | Attempts GLPI session initialization; explicit unconfigured/unavailable status |
| GET `/api/tickets` | Session + linked GLPI ID | Lists tickets through GLPI search API; limit/range 0–49 |
| GET `/api/tickets/{id}` | Session + linked GLPI ID | Fetches detail; non-admin requester check; unauthorized records return 404 |
| POST `/api/tickets` | Session + linked GLPI ID | Creates a ticket; body `{name,content}` with server validation |
| POST `/api/assistant` | Session | Body `{message}` (1–4000 chars); server-side compatible chat completions provider |
| GET `/api/stocks/entities` | Session | Admin sees 7 provisional codes; other users see only their assigned code; no balances are returned |
| GET `/api/stocks` | Session | Intentionally returns 503 until a version-compatible GLPI stock module/API is configured and verified; no parallel ledger |
| GET `/api/admin/entities` | Admin | Lists provisional stock codes and local GLPI ID mapping (ID existence is not verified) |
| POST `/api/admin/entities` | Admin | Map code/name/id; body `{code,name,glpi_entity_id}`. Mapping is audit-logged but not checked against GLPI |
| GET `/api/admin/users` | Admin | List local identities, roles, stock scope and GLPI user mapping (no password hashes) |
| POST `/api/admin/users` | Admin | Create account; body `{username,password,role,glpi_user_id?,stock_entity_code?}` |

Errors have shape `{"error":"human-readable message"}`. Status codes: 400 validation, 401 authentication, 403 role/identity policy, 404 absent/unauthorized ticket, 413 request too large, 503 integration/configuration unavailable, 502 upstream failure. Do not treat a configured integration as verified until its health endpoint passes against the intended GLPI instance.

**Limitations requiring validation before production:** GLPI REST API v1 authentication, searchable fields/criteria, ticket requester fields, and payload formats vary by GLPI release/configuration. Current API client uses the legacy `/apirest.php` shape and requires a controlled test instance to confirm field IDs and role scoping. The shared configured GLPI user token must not grant broader permissions than this application. For meaningful per-user enforcement, use individually scoped GLPI credentials or a tested identity/permission mapping; merely associating a local account with a GLPI numeric ID does not prove GLPI authorization equivalence.