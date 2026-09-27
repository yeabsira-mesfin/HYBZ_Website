# Threat model

## Assets and trust boundaries

Protect organization documents, session credentials, investigation evidence, evaluation reports, and approval authority. Browser requests, uploaded text, retrieved content, and model output are untrusted. User identity and role originate only from the server-side session store.

## Controls and verification

| Threat | Implemented boundary | Evidence |
|---|---|---|
| Cross-organization access | Tenant predicates on all protected records | API isolation tests |
| Role forgery | Session identity; request schemas reject extra fields | Forged-role and viewer tests |
| Session theft/reuse | HttpOnly, SameSite=Strict, one-hour expiry, rotation and revocation | Session tests |
| CSRF | Required custom header, origin allowlist, no cross-origin CORS | Header and foreign-origin tests |
| Prompt injection | Heuristic signals plus deterministic capability boundaries | Bypass cases documented; never a complete defense |
| Data disclosure | Known-pattern redaction before model input/output; metadata-only audit | Redaction and audit tests |
| Resource abuse | Request size cap, per-identity/IP database quotas, model timeout and output limit | Body-limit and atomic-budget tests |
| Model-generated XSS | React text rendering, no HTML injection, CSP | Browser smoke checks |
| Unreviewed containment | Two distinct identities, admin approval, single-use state transition | Incident project approval tests |

## Residual risk

This is a single-node portfolio demonstration, not a production security product. SQLite is not encrypted here. Anyone with filesystem access can read or modify the database and audit events. The seeded accounts share a demo password; no public registration, SSO, MFA, account recovery, or password reset is implemented. Run on loopback with synthetic data.

Prompt-injection detection is a small regular-expression heuristic. Paraphrases, encoding, multilingual instructions, and splitting malicious instructions can bypass it. Redaction misses unknown secret formats and contextual personal data. An optional model can hallucinate or follow malicious authorized content. A model is never an authorization engine.

The default demo is deterministic. Offline results must not be presented as real-model robustness, operational SOC performance, or production deployment experience. Rate buckets and sessions are shared through one database, not a distributed identity platform. In-process background ingestion can be interrupted on restart; reindex with `python -m secure_ai.reindex` in Vaultwise.

## Before production

Integrate OIDC/MFA and unique user provisioning, HTTPS and secure cookies, secrets management, encrypted storage and backups, distributed queues and quota enforcement, retention controls, a remote append-only audit sink, model-specific adversarial evaluations, and infrastructure hardening. Review license and data rights before loading non-synthetic documents. These are explicit future tasks, not completed features.
