# Authorization contracts POC

## User intent

- Authorization intent is explicit in semantic Python symbols and recognizable code structure. Linters/SAST check missing/mismatched/bypassed declarations and wiring; reviewed application code owns business authorization correctness.
- Flexible composite authorization is required. Repository owners choose policy names and implementations; the reusable layer must not prescribe staff roles, ORM, UUIDs, or ownership conventions.
- Full refactoring authorized and preferred. Core belongs under app/ in its own package; business policies under app/api/. Do not restore a checked-in endpoint manifest: discover the mounted FastAPI application.
- PUBLIC and endpoint policy overrides are blocking scanner findings; deliberate rule-specific suppressions need justification and remain visible. Protect implementations, called helpers, and enforcement tools with CODEOWNERS and required reviews.
- Do not reintroduce the previously rejected DB row-level-security design.

## Implemented structure

- app/authz/{contracts,router,discovery}.py: Policy classes, immutable named Binding(resource types, provider) objects, FromPolicy dependencies, mandatory PolicyRouter(protected_policy=...), PUBLIC, use_policy, and live discover_contracts(app).
- Providers execute via normal FastAPI dependency injection. The router validates binding membership and supported methods, installs principal dependencies first, and retains per-route metadata without rewriting endpoint functions.
- app/api/deps.py: authentication/current-user/session primitives only.
- app/api/policies/: AuthenticatedPolicy plus RecordPolicy, OwnerOrStaffNotesPolicy (RecordBase+RecordNoteBase composite), UserPolicy, LoginPolicy, HealthPolicy, VendorPreviewPolicy. Ownership and role checks are normal reviewed Python/SQLModel code here.
- Asset families are explicit resource symbols, independent of provider return types and HTTP schemas. RecordPolicy binds RecordBase; notes additionally bind RecordNoteBase. Do not infer permission from sibling classes or ancestry. Base classes or separate domain marker classes may express the repository's intent.
- RecordPage/RecordNotes TypedDict payloads contain Sequence[Record]/Sequence[RecordNote]; routes retain precise public response_model schemas. Providers do not need per-row public-model conversions. Never weaken a public schema to a base type just to align asset symbols: subclass-only response fields could disappear. Keep the actual provider result type in endpoint annotations; FastAPI performs public response projection.
- Routes consume Annotated[T, FromPolicy(Policy.binding)]. /me moved to users; records and search share RecordPolicy. Explicit notes override preserves owner OR staff, ordinary record/list/search stay owner-only including staff.
- Removed old Scope/Access/__access__, generic Owned/AnyOwner loaders, snapshot walker and policy.json, and generated status matrix. Existing behavioral API tests retained; discovery and standalone contract tests replace structural snapshot tests.
- app/authz imports no application modules or ORM. FastAPI 0.141 private lazy include traversal is isolated and tested. Unsupported mounts/websockets fail explicitly.

## Enforcement and verification

- .semgrep/fastapi-access-control.yaml + fixture: 11 ERROR rules for required policy/bindings, imported wiring aliases, policy mismatch, raw deps, route imports/direct provider calls, policy definition placement, PUBLIC uses and overrides. Asset families, provider types, and public schemas are independent; no ancestry/DTO matching.
- authz-binding-policy-mismatch checks each consumed binding against the endpoint override when present, otherwise the router policy. A correct binding alongside an incorrect one cannot hide the mismatch. Fixtures cover RecordPage/RecordNotes public projection, shared-base composite declarations, same-family wrong policies, overrides, mixed bindings, and consistent import aliases.
- Scanner limitation: policy comparison uses local symbol spelling. Use the same imported policy name in router/override and FromPolicy; two different aliases for one policy can be conservatively flagged. Core runtime validation independently checks actual binding membership. Do not implement ad hoc sibling-class permission inference to work around a scanner limitation.
- Existing .github/scripts/semgrep_gate.py runs rule fixtures, full app/ contract scan independent of baselines, and suppression comment audit. Accepted exceptions printed. Same path in existing local hook and CI; no added hook.
- tests/authz: framework tests independent of DB; tests/scanners: gate/audit tests. Compose test hook mounts .github read-only for gate tests. tests/api/test_contracts.py discovers protected endpoints and independently verifies auth and staff isolation.
- Verification: initial POC full suite passed 89 tests. Asset/result/schema separation then passed 18 standalone contract tests plus 27 real-Postgres API tests, Pyright, mypy, and Ruff. Current Semgrep update passed all 11 rule fixture suites and the full app/ contract scan with visible justified exceptions. The new override-mismatch fixture failed before the rule fix and passes afterward. Earlier throwaway git repositories proved unapproved PUBLIC/missing-policy block, justified exception passes visibly, blanket suppression blocks.
- .github/CODEOWNERS explicitly protects contract layers, helpers, policies, tests, rules, and tooling. Read-only check 2026-09-05: main ruleset already requires code-owner approval, stale-review dismissal and last-push approval. Semgrep and behavioral test status checks still need to be required server-side; no remote settings changed. docs/access-control.md documents the exact review/deployment steps and POC limits.

See docs/access-control.md for runnable usage and architecture. Related: `mem:core`, `mem:conventions`.
