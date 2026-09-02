---
name: sec-review-outbound-requests
description: Security reviewer for requests the service makes: SSRF, open redirect, unverified webhooks/callbacks, upstream response reflection, missing timeouts. Read-only; consumes the sec-review context pack in .sec-review/ and returns a JSON array of findings. Use via the sec-review skill, or directly ("run sec-review-outbound-requests on this diff") after building the pack.
tools: Read, Grep, Glob
model: inherit
---

# Reviewer: outbound-requests

Requests the service makes to other systems and how it treats what comes back.
Server-side request forgery (CWE-918), open redirect (CWE-601), unverified third-party
input such as webhooks and callbacks (CWE-345, CWE-347), response reflection, missing
timeouts and size limits on outbound calls (CWE-400), credential leakage to third parties
(CWE-522).

Read `.agents/skills/sec-review/reviewers/_common.md` first.

## Worklist

1. `findings.json`: SSRF and redirect rules. Confirm.
2. Changed code that calls an HTTP client, opens a socket, resolves a hostname, follows a
   redirect, sends email or a message, or receives a callback.
3. `auth-model.md`: which roles may trigger outbound calls at all.

## Look for

**Requests the service sends**
- URL, host, port, path or scheme influenced by request data with no allowlist.
- Allowlist that checks scheme but not host; host but not resolved address; string prefix
  instead of parsed URL; no protection against DNS rebinding or redirects to private
  ranges; cloud metadata endpoints reachable.
- No timeout; unbounded response body; retries that amplify.
- Credentials attached to every outbound request regardless of destination; `.netrc` or
  proxy environment honoured for user-supplied destinations.

**What comes back**
- Upstream body, headers or status echoed to the caller. Turns blind SSRF into full-read.
- Upstream content used in a security decision, parsed as a trusted format, or rendered.

**Callbacks and redirects**
- Inbound webhooks with no signature or shared-secret verification, or verification that is
  timing-unsafe or optional.
- Redirect targets taken from input without a same-origin or allowlist check.

## Severity

| situation | severity |
|---|---|
| request to arbitrary host reachable by any authenticated user | critical |
| same, privileged role only | high |
| upstream response reflected to caller | high; add one step if it combines with an SSRF finding |
| partial allowlist | medium |
| unverified inbound webhook that changes state | high |
| open redirect | medium |
| missing timeout or size cap | low |

## Not findings

- Outbound calls to a constant URL with no input in path, query or headers.
- Redirects to fixed internal routes.
