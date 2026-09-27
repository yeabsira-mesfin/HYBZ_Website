# Vaultwise: engineering decisions

## Why a self-contained demo

A recruiter can run the application without a paid API account or external database. FastAPI owns authentication and policy enforcement; React renders typed API responses; SQLite provides transactions and queryable evidence. Model capabilities are optional and cannot extend application permissions.

## Identity and resource boundaries

Users authenticate with scrypt-hashed passwords. The browser receives a random opaque cookie; the database stores only its digest. Sessions expire after one hour and are revoked on logout or rotation. Tenant and role come from the server session rather than client parameters. Mutating requests require a same-origin custom header; only explicitly allowed origins pass.

## Evidence over claims

The retrieval engine uses term-frequency and inverse-frequency scoring over authorized chunks. This is lexical RAG, not embedding-based semantic search. SQLite makes the demo self-contained; PostgreSQL/pgvector is a documented future extension, not an implemented dependency.

In-process ingestion returns HTTP 202 and can be recovered after interruption with `python -m secure_ai.reindex`. The `/api/ask/stream` endpoint sends the completed answer as SSE chunks; it is not token-level model streaming. The UI uses the JSON endpoint.

Model usage tokens are reported when Ollama provides them. Cost is `null` because local compute cost is not measured. Citations identify supplied sources; generated claims are not automatically verified for entailment.

## Next engineering milestones

1. Move identity to OIDC with MFA and unique user provisioning.
2. Migrate the store to PostgreSQL with migrations and database-level tenant policies.
3. Add model-specific evaluation datasets and independent human review of generated answers.
4. Move ingestion and long jobs to durable workers with retries and idempotency keys.
5. Add structured observability, load tests, and production retention controls.

These milestones are not implemented. Describe only completed functionality when discussing the project in applications.
