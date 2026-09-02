# Reviewer: injection

Class: untrusted data reaching an interpreter or I/O sink. SQL (CWE-89), OS command
(CWE-78), SSRF (CWE-918), path traversal (CWE-22), template/eval (CWE-94/95), header
injection (CWE-113), unsafe deserialization (CWE-502).

## Read, in order

1. `MANIFEST.md`, then `route-map.md` — every request parameter is a potential source.
2. `findings.json` — semgrep/bandit/CodeQL usually **do** catch this class. Start from their
   hits: confirm, upgrade confidence, and fill in `why_here`. A scanner hit you confirm is
   deterministic evidence.
3. `diff.patch` / changed files — look for what the scanners missed: sinks reached through
   a helper, string building split across lines, f-strings assembled before the call.

## Sinks to trace to

| sink | look for |
|---|---|
| SQL | `execute(`, `executemany(`, `text(`, any string with `SELECT/INSERT/UPDATE/DELETE` built with `f"`, `%`, `.format`, `+` |
| command | `subprocess`, `os.system`, `os.popen`, `shell=True` |
| outbound HTTP | `requests.*`, `httpx.*`, `urllib` with a URL that contains request data — this is SSRF. Check scheme allowlist, host allowlist, DNS/redirect handling, private-range blocking, `allow_redirects`, timeouts |
| filesystem | `open(`, `Path(`, `os.path.join` with request data; `send_file` |
| eval | `eval`, `exec`, `pickle.loads`, `yaml.load` without `SafeLoader`, `jinja2.Template(` from request data |

## Procedure

For each sink in changed code: name the source parameter, trace it to the sink, list every
transformation on the way and whether it neutralizes the injection (parameterization,
allowlist, `shlex.quote`, `pathlib` + `resolve()` + prefix check). If nothing does, flag.

Partial mitigations are still findings at lower severity (e.g. SSRF with a scheme check but
no host check → medium; blocks `file://` but not `http://169.254.169.254`).

## Severity

| situation | severity |
|---|---|
| SQL/command injection reachable by any authenticated user | critical |
| SQL/command injection reachable by staff only | high |
| SSRF to arbitrary host, staff-only | high (internal network + metadata endpoints) |
| SSRF with partial controls | medium |
| path traversal read | high; write → critical |
| unsafe deserialization of request data | critical |

## Confidence

high = source, sink, and absence of neutralizer all quoted. medium = sink is in a helper
you can see but the call site's argument origin is unclear. low = you suspect a sink in an
unchanged file not in the pack — say which file.

## Evidence

Scanner hit that you confirmed → `kind: scanner`, `ref: <rule id>`, `deterministic: true`.
No scanner hit → `kind: reasoning`, `deterministic: false`, and give the verifier a
concrete payload to try (e.g. `q=' OR 1=1 --`, `callback_url=http://127.0.0.1:8000/health`).

## Not findings

- Parameterized queries, even ugly ones.
- Outbound requests to a constant URL.
- Test code building SQL for fixtures.
- Pure data validation gaps with no interpreter downstream (that's `data-exposure` or nothing).

## Output

JSON array of `finding` (`schema.json`), `class: "injection"`, ids `injection-<n>`.
