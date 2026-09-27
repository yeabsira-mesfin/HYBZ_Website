# Vaultwise

### Secure Enterprise Knowledge Assistant

[![Quality gates](https://github.com/yeabsira-mesfin/vaultwise-secure-knowledge/actions/workflows/secure-ai.yml/badge.svg)](https://github.com/yeabsira-mesfin/vaultwise-secure-knowledge/actions/workflows/secure-ai.yml)

A runnable security engineering portfolio project by **Yeabsira Mesfin**, built with Python, FastAPI, React, TypeScript, and SQLite.

![Application dashboard](docs/desktop.webp)

[Mobile screenshot](docs/mobile.webp)

## What works

- Session-authenticated organizations and administrator, analyst, and viewer roles.
- Text/Markdown ingestion, chunking, redaction, and role filtering before lexical retrieval.
- Evidence-linked answers, document deletion with cascading chunk removal, and metadata-only audit logs.
- Prompt-injection signals and quarantine for known suspicious content.
- Optional local Ollama generation; default extractive mode needs no model or API key.
- React/TypeScript dashboard, file upload, source inspection, and responsive layouts.

## Public demo

The Vercel deployment serves the interactive Vaultwise sample, not the archived HYBZ pages. Choose a synthetic persona and ask document questions. The server runs the same retrieval, role filters, redaction, and injection checks against a fresh temporary sample corpus per request. No login, uploads, saved conversations, or paid model calls are enabled on this public demo. Persona selection is not authentication. Use synthetic questions only.

`app.py` is the public Vercel entry point. `secure_ai.api:app` remains the full authenticated local application below. `vercel.json` builds the React public-demo interface into `public/`; the old root `index.html` is not served. No database or model secrets are needed for the public sample.

## Run locally

Requires Python 3.12+ and Node.js 24. Run commands from this repository root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cd dashboard
npm ci
npm run build
cd ..
python -m secure_ai.seed
python -m uvicorn secure_ai.api:app --host 127.0.0.1 --port 8011
```

On Windows PowerShell, replace the activation command with `.venv\Scripts\Activate.ps1`. The other commands are the same.

Open **http://127.0.0.1:8011**. The seed command prints a generated demo password for the five synthetic accounts. It creates accounts only once and does not reset existing passwords. Keep the demo on loopback and use synthetic data.

| Account | Organization | Access |
|---|---|---|
| `admin@alpha.test` | Alpha | Administrator |
| `analyst@alpha.test` | Alpha | Analyst |
| `viewer@alpha.test` | Alpha | Read-only viewer |
| `reviewer@alpha.test` | Alpha | Separate approving administrator |
| `admin@beta.test` | Beta | Administrator in a different organization |

To choose a repeatable demo password, set `DEMO_PASSWORD` to a value of at least 16 characters before seeding. Do not commit it. The database is created in ignored `data/`; delete that directory only when you intentionally want to discard the demo data and reseed.

## Demonstration walkthrough

1. Sign in as `admin@alpha.test` and ask about remote access or incident response.
2. Ask about privileged recovery and inspect the source reference.
3. Sign out, switch to `viewer@alpha.test`, and ask the same privileged question. No privileged source is retrieved.
4. Upload a document as an administrator, ask a matching question, then delete it and verify its chunks disappear.
5. Switch to `admin@beta.test` to inspect a separate organization.

## Architecture

```mermaid
flowchart TD
  B[Browser] --> A[Session and role checks]
  A --> Q[Authorized SQL retrieval]
  Q --> P[Content policy]
  P --> M[Extractive or local model]
  M --> R[Answer and source references]
  A --> L[Metadata audit]
```

The retrieval engine uses term-frequency and inverse-frequency scoring over authorized chunks. This is lexical RAG, not embedding-based semantic search. SQLite makes the demo self-contained; PostgreSQL/pgvector is a documented future extension, not an implemented dependency.

In-process ingestion returns HTTP 202 and can be recovered after interruption with `python -m secure_ai.reindex`. The `/api/ask/stream` endpoint sends the completed answer as SSE chunks; it is not token-level model streaming. The UI uses the JSON endpoint.

Model usage tokens are reported when Ollama provides them. Cost is `null` because local compute cost is not measured. Citations identify supplied sources; generated claims are not automatically verified for entailment.

## Verification

```bash
python -m pytest -q
python -m bandit -r secure_ai -q
python -m pip_audit -r requirements.lock
cd dashboard
npm ci
npm run build
npm audit --audit-level=moderate
```

The backend suite contains **21 tests**. See [verification notes](docs/VERIFICATION.md) for what was actually run and the limits of those checks. CI repeats backend tests, static security checks, dependency auditing, and frontend compilation.

## Docker

```bash
docker compose up --build
```

The container runs as a non-root user with a read-only root filesystem, a writable named data volume, dropped capabilities, and a loopback-only published port. The generated demo password appears in the initial container logs. Docker files are provided; check the verification notes for whether a container build was executed in the authoring environment.

## Project structure

- `secure_ai/`: application services, policies, authentication, and persistence.
- `dashboard/`: the new React/TypeScript application.
- `tests/`: authorization, isolation, session, and product behavior tests.
- `docs/`: threat model, verification, and engineering notes.
- `.github/workflows/secure-ai.yml`: continuous verification.

Earlier website/exercise files remain at the root to preserve the existing project and history. They are not served by this application or copied into its Docker runtime. Use `dashboard/`, not the old root frontend, for this project.

## Security and limitations

Read the [threat model](docs/THREAT-MODEL.md). This is a local portfolio demonstration, not a production security product. Authentication, tenant predicates, and approval rules are enforced in application code; a model never decides authorization. Regex-based injection detection and redaction are incomplete. SQLite and local audit records are not encrypted or tamper-proof here.

## Related projects

- [Vaultwise](https://github.com/yeabsira-mesfin/vaultwise-secure-knowledge): secure knowledge retrieval.
- [ProbeLab](https://github.com/yeabsira-mesfin/probelab-ai-security): policy evaluations and API integration checks.
- [Traceguard](https://github.com/yeabsira-mesfin/incident-investigation-agent): constrained incident investigation.

## Author

[Yeabsira Mesfin](https://www.linkedin.com/in/yeabsira-mesfin-76379928a) · [Portfolio](https://yeabsira-mesfin.vercel.app/) · [GitHub](https://github.com/yeabsira-mesfin)

## Optional local model

Install Ollama separately and pull a model suitable for your hardware. In the same shell used to start the API:

```bash
export MODEL_MODE=ollama
export OLLAMA_MODEL=your-installed-model
```

PowerShell: `$env:MODEL_MODE="ollama"` and `$env:OLLAMA_MODEL="your-installed-model"`.

Restart the API. The adapter calls the fixed local `http://127.0.0.1:11434/api/chat` endpoint with a 45-second timeout. In native mode both processes must run on the same host. The provided Docker configuration uses the extractive demo mode; it does not automatically connect to a host Ollama installation. A live model was not available during authoring, so live generation is not claimed as verified.
