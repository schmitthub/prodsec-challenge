# Lens: data-exposure

Information reaching the wrong party. Error details and stack traces (CWE-209, CWE-497),
over-broad responses and serialisation (CWE-200, CWE-359), sensitive data in logs (CWE-532),
debug and introspection surfaces (CWE-489), behavioural oracles (CWE-204), sensitive data
cached or persisted where it should not be (CWE-524, CWE-312).

Read `_common.md` first.

## Worklist

1. `findings.json`: error-handling and logging rules.
2. `route-map.md`: the `response_model` column. A handler returning a raw object or dict
   instead of a declared model is where over-exposure hides.
3. Changed exception handlers, middleware, logging calls, response models, serialisers,
   and any code that renders internal state into a response.

## Look for

**Errors**
- Handlers returning exception text, repr, class name or traceback to clients.
- Error details carrying internal state: query text, paths, hostnames, other users' ids.
- Different status or body for "does not exist" vs "not yours" on tenant-scoped resources.
  The missing check is `access-control`; the oracle is yours.

**Responses**
- Objects serialised with credential, hash, token, or internal fields present.
- Collections that include other tenants' identifiers or metadata.
- Full records where the caller needs a subset.

**Logs and persistence**
- Request bodies, authorisation headers, tokens, secrets or personal data in logs.
- Sensitive data written to caches, temp files or analytics without need.

**Surfaces**
- API docs, schema, debug toolbars, profilers, admin consoles exposed without an
  environment gate. Rate by what they reveal and by what `auth-model.md` accepts.
- Debug mode or auto-reload in a production entrypoint.
- Verbose server, framework or version headers.

## Severity

| situation | severity |
|---|---|
| credentials or tokens in logs or responses | high |
| exception text to client | medium; high if it can include secrets or query text |
| other tenants' data in a response | high (also raise with `access-control` if the check is missing) |
| existence oracle on tenant resources | low |
| docs, schema or debug surface exposed | low unless it reveals secrets or internal hosts |

## Not findings

- Generic error messages with a stable status code.
- Logging at debug level with no personal or secret data.
