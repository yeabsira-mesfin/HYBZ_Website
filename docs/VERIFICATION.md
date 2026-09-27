# Verification record

Verified locally on 2026-09-27 using Python 3.12, Node.js 24, and Chromium 134.

| Check | Result |
|---|---|
| Backend functional and security suite | 19 tests passed |
| Bandit scan of `secure_ai/` | No findings |
| TypeScript compilation and Vite production build | Passed |
| Python dependency audit of shared locked environment | No known vulnerabilities reported |
| npm dependency audit of shared dashboard dependency versions | No known vulnerabilities reported |
| Browser workflow at desktop width 1440 | Passed |
| Browser workflow at mobile width 390 | Passed; no horizontal page overflow |
| Browser runtime and CSP errors during tested workflow | None observed |

The browser checks exercised login, the primary product workflow, audit navigation, and responsive layout. Traceguard additionally exercised the second-user approval workflow. Screenshots in this directory were captured from the running applications, not design mockups.

Vaultwise also passed ten HTTP integration checks from ProbeLab, covering tenant and role isolation, citations, extra-field rejection, cross-tenant deletion, viewer write denial, known injection signals, suspicious-context exclusion, origin checks, and logout revocation. ProbeLab stores the integration report in `benchmarks/knowledge-integration.json` and a reproducible policy fixture result in `benchmarks/policy-test.json`.

## Verification limits

- A Starlette test-client deprecation warning was observed; tests still passed.
- No live Ollama model was available. Generation integration is included but no real-model quality or security result is claimed.
- Docker is not installed in the authoring environment, so container builds were not executed locally.
- No public hosting deployment, operational incident response, load benchmark, or production security certification is claimed.
- Audits describe the locked new application dependencies at the time of the scan. Earlier exercise files retained in the repository are outside the new runtime and were not audited as part of this build.

CI is configured to repeat backend tests, Bandit, dependency audits, frontend builds, and the ProbeLab regression gate. Check the repository Actions page for remote CI status; local results do not imply that a remote run completed.
