# Triage 

## Code Security Issues

- dev.py api key. switch to env var and leverage python-dotenv 
- fixture_secrets.py secret import gate is brittle and will cause failures if pytest specifically isn't used, and it appears its not. it also should realistically moved to the test harness and be kept out of prod code entirely `TODO: confirm issues with unittest package` 
- auth.py JWT_SECRET use secrets.token_urlsafe(32)
- webooks.py `PreviewRequest.callback_url` should be validated to prevent SSRF attacks
- login.py user and password conditional is technically vuln to timing attacks but not sure if it's out of scope due to the DB being faked for the purpose of the challenge
- search.py broken access control. only checks if user is authenticated, not if they have permission to access specific records
- db.py sql injection in search_records
- records.py broken access control. only checks if user is authenticated, not if they have permission to access specific records
- Dockerfile runs as root user


### False Positive

- fixture_secrets.py has a test only key 

### Info / Quality 

## Package Vulnerabilities

| priority | package | cvss | vuln id |
|---------|----------|------|---------|
| medium | starlette@0.50.0 | | CVE-2026-54283 |