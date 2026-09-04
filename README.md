# Records API Security Take-Home

> [!IMPORTANT]
> **For Reviewers**
>
> - Local setup: [`CONTRIBUTING.md`](CONTRIBUTING.md)
> - Deliverables
>   - [`Write-Up`](challenge/deliverables/write-up.md)
>   - [`AI Security Review`](challenge/deliverables/ai-security-review.md)
>   - [`AI Tools Usage`](challenge/deliverables/ai-usage.md)
>   - [`Remediation Message`](challenge/deliverables/remediation-message.md)
>

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

- `alice@example.com` / `alice-password`
- `bob@example.com` / `bob-password`
- `clinician@example.com` / `clinician-password`

Get a token with:

```bash
curl -s -X POST http://127.0.0.1:8000/api/login \
  -H 'content-type: application/json' \
  -d '{"email":"alice@example.com","password":"alice-password"}'
```

Then pass the returned token as a bearer token:

```bash
curl -H "authorization: Bearer <token>" http://127.0.0.1:8000/api/records
```
