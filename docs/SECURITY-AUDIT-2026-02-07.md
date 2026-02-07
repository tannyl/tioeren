# Security Audit Report - 2026-02-07

## Executive Summary

Comprehensive security audit of the Tiøren personal finance application.

| Test | Result | Findings |
|------|--------|----------|
| SEC-001: Static Analysis (SAST) | PASS | 0 findings from 826 rules |
| SEC-002: Dependency Scan (SCA) | PARTIAL | 6 vulns (dev-time, low-moderate) |
| SEC-003: Authentication Testing | PARTIAL | 1 MEDIUM, 3 LOW |
| SEC-004: Authorization (BOLA/IDOR) | PASS | 18/18 tests passed |
| SEC-005: Input Validation (Injection) | PASS | SQLi + XSS protected |
| SEC-006: API Security & Business Logic | FAIL | 1 HIGH, 5 MEDIUM, 1 LOW |

## Severity Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | - |
| HIGH | 1 | Fix before production |
| MEDIUM | 5 | Fix recommended |
| LOW | 5 | Track for future |

## HIGH Severity Issues (Fix Before Production)

### VULN-H1: Missing Rate Limiting
- **Location:** All API endpoints
- **Impact:** Brute force attacks on login, DoS potential
- **Recommendation:** Implement slowapi middleware with per-IP limits

### ~~VULN-H2: Weak Default SECRET_KEY~~ (FALSE POSITIVE)
- **Status:** Not a vulnerability
- **Reason:** SECRET_KEY is defined in config but **never used** in the codebase
- **Details:** Sessions use database-stored UUIDs with HttpOnly cookies, not JWT or signed tokens. The `settings.SECRET_KEY` value is never referenced anywhere.
- **Action:** Reserved for future use (e.g., JWT signing). No fix needed.

## MEDIUM Severity Issues

### VULN-M1: Missing HTTP Security Headers
- **Location:** `api/main.py`
- **Headers needed:** CSP, X-Content-Type-Options, X-Frame-Options, HSTS
- **Recommendation:** Add security headers middleware

### VULN-M2: DEBUG Mode Enabled
- **Location:** `.env`
- **Recommendation:** Set DEBUG=False by default

### VULN-M3: API Documentation Exposed
- **Location:** `/docs`, `/redoc`, `/openapi.json`
- **Recommendation:** Disable when DEBUG=False

### VULN-M4: Insecure Session Cookies
- **Location:** `api/routes/auth.py`
- **Issue:** Secure flag disabled when TESTING=True
- **Recommendation:** Use explicit PRODUCTION flag

### VULN-M5: No Negative Amount Validation
- **Location:** Account/Transaction creation
- **Recommendation:** Add business logic validation

### VULN-M6: Vulnerable npm Dependencies
- **Packages:** cookie, esbuild (via @sveltejs/kit, svelte-i18n)
- **Recommendation:** Update dependencies, add npm audit to CI

## LOW Severity Issues

- npm vulnerabilities (dev-time only, moderate severity)
- API docs exposure (development convenience)

## False Positives (Dismissed)

- **SECRET_KEY:** Defined but never used. Sessions use database UUIDs, not cryptographic signatures.

## Security Strengths

The application demonstrates solid security practices:

1. **Authentication:** bcrypt password hashing, HttpOnly cookies, SameSite=strict
2. **Authorization:** Proper user isolation, returns 404 (not 403) to prevent enumeration
3. **SQL Injection:** SQLAlchemy ORM with parameterized queries
4. **XSS:** Svelte auto-escaping, @html only for controlled SVGs
5. **CORS:** Whitelist-based configuration
6. **Session Management:** UUID tokens, proper logout invalidation
7. **Error Handling:** No stack traces in responses

## Recommended Actions

### Before Production (Priority 1)
1. Implement rate limiting on auth endpoints
2. Set DEBUG=False and TESTING=False

### Near-term (Priority 2)
3. Add HTTP security headers middleware
4. Disable API docs when DEBUG=False
5. Update npm dependencies

### Backlog (Priority 3)
6. Add business logic validation for negative amounts
7. Monitor dependency updates

## Test Evidence

- Semgrep scans: 826 rules across backend + frontend
- npm audit: Full dependency tree
- Dynamic tests: 18 BOLA/IDOR tests, SQLi payloads, XSS vectors
- Screenshots: `.playwright-mcp/sec-005-xss-escaped.png`
