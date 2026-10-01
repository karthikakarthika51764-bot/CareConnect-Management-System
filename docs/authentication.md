# Authentication and Authorization

Passwords are hashed with Argon2id using `pwdlib`. Access tokens are signed HS256 JWTs with a short expiry. Refresh tokens have a separate token type, 14-day expiry, unique token ID, and only a SHA-256 digest is stored; refresh rotates and rejects replay. Logout clears the stored refresh digest. Access tokens remain valid until expiry, as is typical for stateless bearer tokens.

The API resolves user ID from the signed access-token subject and reloads the active user record on each protected request. Role decisions happen on the server. Business IDs come from that user record rather than client input. Current roles are SUPER_ADMIN, BUSINESS_OWNER, STAFF, and RECEPTIONIST. Registration creates a BUSINESS_OWNER; staff creation is limited to STAFF or RECEPTIONIST accounts.

`require_roles(...)` is applied to sensitive write routes. This is role-based access control at present; the permission names in the project brief are not yet implemented as independently configurable permission grants. Do not treat frontend navigation as an authorization boundary.

Production must provide a high-entropy `SECRET_KEY`, restrict CORS origins, use TLS, rotate provider secrets, and use a shared rate limiter. The included limiter is process-local and suitable only for a single development instance.
