# Records API Security Take-Home

> [!IMPORTANT]
> **Reviewers: submission index.** Everything the brief asks for, in one place.
>
> | Deliverable | Where |
> | --- | --- |
> | 1. CI pipeline | [`.github/workflows/`](.github/workflows/) — `pr.yml` / `main.yml` call [`security.yml`](.github/workflows/security.yml) (semgrep, bandit, gitleaks, image scan, dependency review) and [`test.yml`](.github/workflows/test.yml); [`codeql.yml`](.github/workflows/codeql.yml); [`release.yml`](.github/workflows/release.yml) → [`image.yml`](.github/workflows/image.yml) + [`build.yml`](.github/workflows/build.yml) (signed, attested, SBOM'd release). Local mirror of the same gates: [`.pre-commit-config.yaml`](.pre-commit-config.yaml) via the shared [`semgrep_gate.py`](.github/scripts/semgrep_gate.py). |
> | 2. Custom detection (broken access control) | [`tests/test_authz_invariant.py`](tests/test_authz_invariant.py) — walks every authenticated route and fails when a member's response contains another user's identifiers. |
> | 3. Triage write-up | [`challenge/deliverables/write-up.md`](challenge/deliverables/write-up.md) (working notes: [`challenge/notes/triage.md`](challenge/notes/triage.md)) |
> | 4. Remediation message | TODO(andrew): not yet written — link it here |
> | 5. AI-assisted PR security reviewer | [`challenge/deliverables/ai-security-review.md`](challenge/deliverables/ai-security-review.md) — design; a lite local implementation ships as the [`sec-review`](.agents/skills/sec-review/) agent skill. |
> | 6. AI tools usage note | [`challenge/deliverables/ai-usage.md`](challenge/deliverables/ai-usage.md) |
>
> Local setup, hooks and scanner reports: [`CONTRIBUTING.md`](CONTRIBUTING.md).

This repository contains a small FastAPI service used for the Senior Product Security Engineer take-home.

Start with `challenge/candidate-brief.md`.

## Public Repository Notice

This service is intentionally vulnerable and uses fake local credentials and seeded test secrets for a security exercise. Do not deploy it as-is or reuse any sample values in production.

## Setup

Use Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
```

## Run The API

Running the app manually is not strictly necessary to complete the assignment. You can work from the code, tests, and CI. If you want to reproduce behavior over HTTP, this is a fully functional API.

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

FastAPI's generated docs are available at `http://127.0.0.1:8000/docs` when the service is running.

## Run With Docker

Docker is optional, but it is the quickest way to run the API without setting up a local virtual environment.

```bash
docker build -t records-api .
docker run --rm -p 8000:8000 records-api
```

Check that the API is responding:

```bash
curl http://127.0.0.1:8000/health
```

## Test Accounts

Use these accounts for local testing:

- `alice@example.test` / `alice-password`
- `bob@example.test` / `bob-password`
- `clinician@example.test` / `clinician-password`

Get a token with:

```bash
curl -s -X POST http://127.0.0.1:8000/api/login \
  -H 'content-type: application/json' \
  -d '{"email":"alice@example.test","password":"alice-password"}'
```

Then pass the returned token as a bearer token:

```bash
curl -H "authorization: Bearer <token>" http://127.0.0.1:8000/api/records
```
