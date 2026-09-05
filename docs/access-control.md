# Authorization contracts

This POC captures authorization intent in Python symbols so static analysis can
check declaration and wiring. Reviewed application code owns the actual business
rules. It prevents routine missing-policy and wrong-policy mistakes without
requiring a scanner to infer ownership from arbitrary Python or SQL.

## Separation of responsibilities

| Layer | Responsibility |
|---|---|
| `app/authz/` | Reusable `Policy`, `Binding`, `FromPolicy`, `PolicyRouter`, explicit overrides, live discovery |
| `app/api/deps.py` | Application bearer authentication and session dependency |
| `app/api/policies/` | Reviewed ownership queries, staff checks, credential exchange, outbound controls, composite providers |
| `app/api/routes/` | HTTP paths, response schemas, and consumption of declared bindings |
| `.semgrep/` and `.github/scripts/semgrep_gate.py` | Structural checks, blocking exceptions, suppression audit |
| `.github/CODEOWNERS` and the repository ruleset | Required review of contracts, their implementations, and enforcement tools |

The reusable package imports no application model, settings, SQLModel, role,
UUID convention, or database engine. Its tests use unrelated plain resource
classes, integer keys, and both synchronous and asynchronous handlers.

## Ordinary endpoint

Application policy uses named binding attributes, which are Python symbols:

```python
class RecordPolicy(AuthenticatedPolicy):
    principal: ClassVar[Principal] = staticmethod(record_reader)
    record = Binding((RecordBase,), owned_record)
    page = Binding((RecordBase,), owned_records)
    search = Binding((RecordBase,), search_owned_records)
```

`AuthenticatedPolicy` resolves the bearer to the current database user.
`record_reader` also checks the application's recognized record-reader roles.
The provider functions perform the real owner-filtered queries.

```python
router = PolicyRouter(tags=["records"], protected_policy=RecordPolicy)


@router.get("/records/{record_id}", response_model=RecordPublic)
def read_record(
    record: Annotated[Record, FromPolicy(RecordPolicy.record)],
) -> Record:
    return record
```

`FromPolicy` is an ordinary FastAPI dependency carrying a binding identity.
The router verifies that it belongs to the selected policy and installs the
principal dependency before the providers. It rejects a missing policy, missing
binding, foreign binding, raw endpoint dependency, ambiguous override, or an
unsupported HTTP method. It does not rewrite endpoint signatures.

GET/HEAD are the default supported methods. A policy for a command explicitly
names its methods. The framework does not infer write authorization from a read
scope. Providers may use normal FastAPI dependencies, request models, joins,
transactions, external services, and arbitrary business authorization logic.

Search uses the same `RecordPolicy` in its own module. `/me` is in the users
router, which declares `UserPolicy`.

## Asset families and response types

The resource symbol describes authorization intent independently of the provider's
Python return type and the endpoint's public response schema. Here `RecordBase`
names the record asset family, and `RecordNoteBase` names the note asset family.
Table models and public schemas are siblings under those bases. A project can
also declare a separate domain marker when its representations share no base.

For example, the notes binding declares `(RecordBase, RecordNoteBase)`. Its
provider returns a `RecordNotes` typed dictionary containing `Sequence[RecordNote]`,
the authorized record ID, and the count. The endpoint declares
`response_model=RecordNotesPublic`, so FastAPI validates and serializes that data
into public notes, preserving note IDs while excluding undeclared fields.
List and search use `RecordPage` in the same way. Providers do not need to
construct HTTP response models or convert every database object themselves.

The contract checks the selected policy and binding identity; it does not require
asset, provider, and response types to be identical. It also does not discover
sibling classes or infer permissions from inheritance. A common ancestor such as
`SQLModel` cannot establish shared authorization intent. The explicit asset
declaration and reviewed provider establish that relationship, and the provider
still authorizes the particular objects returned. Public response schemas retain
their precise field types; changing a response field to the asset base could
discard fields only declared by its subclasses.

## Composite endpoint and explicit exception

The record-notes operation demonstrates a provider that protects two resources:

```python
class OwnerOrStaffNotesPolicy(AuthenticatedPolicy):
    principal: ClassVar[Principal] = staticmethod(record_reader)
    notes = Binding((RecordBase, RecordNoteBase), owner_or_staff_notes)
```

The provider enforces authenticated AND (record owner OR staff), then returns
only the notes related to that authorized record. This policy does not expose a
cross-owner record loader or collection loader. Staff still get 404 when reading
another user's record through the ordinary record endpoint, and their list and
search results remain owner-filtered.

The records router keeps its owner-only default. Its notes endpoint explicitly
selects the exception:

```python
@router.get(
    "/records/{record_id}/notes",
    response_model=RecordNotesPublic,
    dependencies=[
        # Product exception: record owners and staff may read this record's notes.
        # nosemgrep: authz-policy-override
        use_policy(OwnerOrStaffNotesPolicy)
    ],
)
def read_record_notes(
    notes: Annotated[RecordNotes, FromPolicy(OwnerOrStaffNotesPolicy.notes)],
) -> RecordNotes:
    return notes
```

Policies can also contain several bindings, including multiple bindings of the
same type. Only consumed bindings execute. Declaring a type is an inventory of
what a provider protects, not an ambient grant to every instance of that type.
Policy names and provider implementations belong to the repository owner.

## Public operations

Login and liveness declare `principal = PUBLIC` in their reviewed policies.
That declaration is an ERROR finding. Applying either public policy to a router
is also an ERROR finding. Each intentional application has its own suppression
and adjacent justification. A public policy grants no special database/session
access to a handler: the handler still consumes a registered provider.

`use_policy(...)` is always flagged; the scanner does not guess whether custom
business logic narrows or widens access. An exception requires a specific rule
ID and a preceding justification comment. Blanket or unjustified suppressions
fail the independent comment audit. Accepted exceptions are printed on every
contract gate run, including those whose primary finding is suppressed.

## Discovery, not an endpoint manifest

`discover_contracts(app)` inspects the mounted application, including lazy nested
router includes and operations omitted from OpenAPI. `app/main.py` invokes it
after mounting the routes; tests also invoke it directly. It verifies that each
operation's principal and selected providers actually appear in its dependency
tree. Metadata belongs to the route registration, not the endpoint function.

There is no checked-in endpoint inventory to generate or maintain. Framework docs
are recognized separately. Uncontracted routes and currently unsupported mounted
subapplications/websockets fail explicitly rather than silently escaping the walk.
The traversal of FastAPI 0.141's private lazy-include API is isolated in
`app/authz/discovery.py` and covered by compatibility tests.

## Scanner and review enforcement

`Principal` is the shared type for every `principal: ClassVar[Principal]`
declaration. A subclass may select a different dependency or PUBLIC, but must
preserve that mutable attribute's type. The shared `scripts/lint.sh` entry point
runs strict mypy with `mutable-override` and `explicit-override` enabled, plus
Ruff's annotation, suppression, mutable-default, async, and correctness rules.
Both pre-commit and the Test workflow call this script using tools from `uv.lock`.
The lint regression tests demonstrate that the narrowed principal annotation is
rejected and the shared declaration passes. Application queries and HTTP response
schemas remain independent of the protected asset symbols.

The existing Semgrep hook and CI job both run:

1. Rule fixtures, including imported aliases, asset-family declarations, typed
   provider results with separate public schemas, and expected non-findings.
2. A full `app/` contract scan, independent of PR/staged-file baselines.
3. An audit of actual Python suppression comments.

General security rules retain their existing incremental behavior. Contract checks
must be full-tree because a policy change can affect unchanged endpoints.

The contract rules check mandatory router policies, required endpoint bindings,
policy/binding name mismatches (including bindings under explicit overrides), raw dependencies, route import boundaries, direct
provider calls, policy definitions outside their reviewed directory, public
policies, public-router applications, and endpoint overrides. These repository
conventions are intentionally explicit; changing them changes the trusted surface.
A new public policy also needs its canonical symbol added to the public-router
rule. Its PUBLIC definition already blocks before that change is accepted.

Asset inheritance and response types do not participate in policy matching.
A `RecordPage` or `RecordNotes` result may use a different public response schema;
sharing an asset family does not make two policies interchangeable. Each consumed
binding must name the selected policy, including when another binding in the same
endpoint is correct. Use the same local policy name in the router/override and
binding expressions. Imported aliases work when used consistently; this POC's
symbol-spelling comparison can flag two different aliases for the same policy.
Runtime validation checks actual binding membership independently.

Semgrep is the executable custom SAST integration in this POC. CodeQL continues
running its existing security suite; it does not yet contain equivalent custom
contract queries. The canonical policy/provider symbols provide the input for
such queries without requiring them for this demonstration.

CODEOWNERS explicitly covers the framework, application policies, authentication,
provider helpers, models, tests, scanner rules, hook/workflow gates, and ownership
configuration. Protect helpers as well as the policy file that imports them.

### Repository settings to complete merge enforcement

Read-only verification on 2026-09-05 found the active `main` ruleset already
requires code-owner approval, one approving review, stale-review dismissal, and
approval after the last push. The CODEOWNERS wildcard also covers all route edits.

The required status checks currently omit **Security / Semgrep SAST**. Before
relying on this contract as a merge gate, add that GitHub Actions check to the
`main` ruleset's required checks, preserving the existing requirements. Also make
the **Test / test** workflow job required to gate behavioral authorization proof.
Select the exact emitted check names after this branch has run in CI; the API's
check-run names can differ from the UI's workflow grouping. No server-side rule
was changed as part of this reviewable POC. Required review needs an eligible
reviewer other than the PR author; configure a security team when collaborating.

## Verification and extension

```bash
bash scripts/lint.sh
uv run pytest --confcutdir=tests/authz tests/authz tests/scanners
# With the pinned Semgrep executable available:
uv run python .github/scripts/semgrep_gate.py --contracts
# Same real-Postgres test path used by the local hook:
docker compose run --build --rm -T \
  -v "$PWD/app:/app/app" -v "$PWD/tests:/app/tests" \
  -v "$PWD/scripts:/app/scripts" -v "$PWD/.github:/app/.github:ro" \
  backend bash scripts/tests-start.sh
```

To add an operation, implement/reuse a reviewed provider, expose it as a policy
binding, and consume that symbol from its route. Put exceptional semantics in a
named application policy and explicitly select it at the endpoint. Add behavioral
proof for the business authorization; route discovery supplies structural coverage.

The framework trusts reviewed providers. It cannot prove that an owner predicate
is correct, that a provider's declared resource inventory is honest, or that all
possible Python I/O is absent from a handler. Scanners enforce supported code
shapes, not a Python sandbox. Existing member/foreign/staff tests inspect real
responses, collection counts, and related rows to verify the business behavior.
