# Lens: input-validation-dos

Input shape and resource limits. Missing or weak validation (CWE-20), type confusion,
unbounded collections and pagination (CWE-770), regex denial of service (CWE-1333),
missing rate limits (CWE-770, CWE-799), decompression and parser bombs (CWE-409),
integer and size handling (CWE-190, CWE-789), unbounded memory or CPU per request.

Read `_common.md` first. Injection into an interpreter is `injection`.

## Worklist

1. `route-map.md`: every parameter and body field. Check what constrains each one: type,
   length, range, pattern, enum, count.
2. Changed request models, validators, query builders, loops over input, regexes,
   file or upload handling sizes, and anything that allocates per item of input.
3. `findings.json` for regex and resource rules.

## Look for

- Fields typed as free string or `Any` where an enum, id format or bounded length applies.
- Query parameters that select a page size, limit, depth, count or repeat with no maximum.
- List or search routes with no pagination, or pagination the client can disable.
- Regex with nested quantifiers or overlapping alternations applied to input.
- Request body size unbounded; JSON depth unbounded; multipart or archive expansion
  unbounded.
- Numeric input reaching arithmetic, allocation or indexing without range checks.
- Login, reset, OTP, search, export and webhook-trigger routes with no per-identity or
  per-source throttling.
- Retries, fan-out, or recursion whose count is driven by input.

## Severity

| situation | severity |
|---|---|
| single request can exhaust CPU or memory (bomb, ReDoS, unbounded expansion) | high |
| unbounded collection route on a large table | medium; high if unauthenticated |
| missing throttling on a credential or cost-bearing route | medium |
| loose types that let a downstream sink misbehave | medium |
| cosmetic validation gaps | info |

## Not findings

- Bounded inputs enforced by the schema layer you can see.
- Rate limiting implemented at a gateway `repo-conventions.md` says exists.
