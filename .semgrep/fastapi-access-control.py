# Scanner fixtures intentionally contain misplaced/unused imports, unresolved
# names, and unused parameters. Keep ruleid/ok comments on their target lines.
# ruff: noqa: ARG001, E402, F401, F821, I001
# fmt: off

from typing import Annotated
from typing import Annotated as Annotation
from app.authz import FromPolicy as Bound
from fastapi import APIRouter, Depends, Security
from app.authz import Binding, FromPolicy, Policy, PolicyRouter, PUBLIC, use_policy
from app.authz import PolicyRouter as RouterAlias
from app.api.policies.records import (
    RecordPolicy,
    OwnerOrStaffNotesPolicy,
    RecordPage,
    RecordNotes,
    owned_record,
    owner_or_staff_notes,
)
from app.api.policies.records import OwnerOrStaffNotesPolicy as NotesPolicy
from app.api.policies.records import RecordPolicy as OwnerPolicy
from app.api.policies.login import LoginPolicy as AnonymousLogin
from app.api.policies.health import HealthPolicy
from app.models import (
    Record,
    RecordBase,
    RecordNoteBase,
    RecordPublic,
    RecordsPublic,
    RecordNotesPublic,
)

# ruleid: authz-router-policy-required
missing = PolicyRouter(tags=["records"])
# ruleid: authz-router-policy-required
alias_missing = RouterAlias()
# ok: authz-router-policy-required
router = PolicyRouter(protected_policy=RecordPolicy)
# ok: authz-router-policy-required
alias_ok = RouterAlias(protected_policy=RecordPolicy)
# ruleid: authz-route-router
raw = APIRouter()

# ruleid: authz-route-binding-required
@router.get("/unbound")
def unbound():
    return {}

# ok: authz-route-binding-required
@router.get("/{record_id}", response_model=RecordPublic)
# ok: authz-binding-policy-mismatch
def bound(record: Annotated[Record, FromPolicy(RecordPolicy.record)]) -> Record:
    return record

# ok: authz-route-binding-required
@router.get("/async/{record_id}")
async def async_bound(record: Annotated[Record, FromPolicy(RecordPolicy.record)]):
    return record

# ruleid: authz-route-raw-dependency
raw_dep = Depends(owned_record)
# ruleid: authz-route-raw-dependency
raw_security = Security(owned_record)

# ruleid: authz-route-import-boundary
from app.core.db import engine
# ruleid: authz-route-import-boundary
from app.api.deps import SessionDep
# ruleid: authz-route-import-boundary
from sqlmodel import Session
# ruleid: authz-route-import-boundary
import requests
# ruleid: authz-route-import-boundary
from app.services import unreviewed_loader
# ok: authz-route-import-boundary
from app.api.policies.users import UserPolicy

# ruleid: authz-route-provider-call
leaked = owned_record(record_id)

# ruleid: authz-policy-definition-boundary
forged_binding = Binding((RecordBase,), owned_record)
# Base-family and composite declarations still belong in reviewed policy files.
# ruleid: authz-policy-definition-boundary
forged_composite = Binding((RecordBase, RecordNoteBase), owner_or_staff_notes)
# ruleid: authz-policy-definition-boundary
class ForgedPolicy(Policy):
    pass

class AnonymousPolicy:
    # ruleid: authz-public-policy
    principal = PUBLIC

# ruleid: authz-public-router
login_router = PolicyRouter(protected_policy=AnonymousLogin)
# ruleid: authz-public-router
health_router = PolicyRouter(protected_policy=HealthPolicy)
# ruleid: authz-policy-override
exception = use_policy(OwnerOrStaffNotesPolicy)


@router.get("/wrong-resource")
# ruleid: authz-binding-policy-mismatch
def wrong_resource(user: Annotated[Record, FromPolicy(UserPolicy.me)]):
    return user

# Product exception: allow staff access to record notes.
# ruleid: authz-policy-override
@router.get("/notes", response_model=RecordNotesPublic, dependencies=[use_policy(OwnerOrStaffNotesPolicy)])
# ok: authz-binding-policy-mismatch
def notes(data: Annotated[RecordNotes, FromPolicy(OwnerOrStaffNotesPolicy.notes)]) -> RecordNotes:
    return data


# ok: authz-route-binding-required
@router.get("/aliases/{record_id}")
def aliased_binding(record: Annotation[Record, Bound(RecordPolicy.record)]):
    return record


# Provider payloads and HTTP schemas are independent of protected asset symbols.
# ok: authz-route-binding-required
@router.get("/records", response_model=RecordsPublic)
# ok: authz-binding-policy-mismatch
def record_page(data: Annotated[RecordPage, FromPolicy(RecordPolicy.page)]) -> RecordPage:
    return data

# ok: authz-route-binding-required
@alias_ok.get("/search", response_model=RecordsPublic)
# ok: authz-binding-policy-mismatch
async def search_page(data: Annotation[RecordPage, Bound(RecordPolicy.search)]) -> RecordPage:
    return data

# Sharing an asset family or response schema does not make policies equivalent.
@router.get("/same-family-wrong-policy", response_model=RecordNotesPublic)
# ruleid: authz-binding-policy-mismatch
def same_family_wrong_policy(data: Annotated[RecordNotes, FromPolicy(OwnerOrStaffNotesPolicy.notes)]) -> RecordNotes:
    return data

# A reviewed override must still select bindings from that override's policy.
# ruleid: authz-policy-override
@router.get("/wrong-overridden-binding", response_model=RecordsPublic, dependencies=[use_policy(OwnerOrStaffNotesPolicy)])
# ruleid: authz-binding-policy-mismatch
def wrong_overridden_binding(data: Annotated[RecordPage, FromPolicy(RecordPolicy.page)]) -> RecordPage:
    return data

# The same imported policy alias is valid on the override and binding sides.
# ruleid: authz-policy-override
@router.get("/aliased-notes", response_model=RecordNotesPublic, dependencies=[use_policy(NotesPolicy)])
# ok: authz-binding-policy-mismatch
def aliased_notes(data: Annotation[RecordNotes, Bound(NotesPolicy.notes)]) -> RecordNotes:
    return data


# An inherited policy also permits a consistently used import alias.
aliased_policy_router = RouterAlias(protected_policy=OwnerPolicy)

@aliased_policy_router.get("/aliased-policy", response_model=RecordsPublic)
# ok: authz-binding-policy-mismatch
def aliased_policy(data: Annotated[RecordPage, FromPolicy(OwnerPolicy.page)]) -> RecordPage:
    return data

# Known POC limit: different local names for one policy are conservatively
# flagged. Use one spelling consistently; no runtime type restriction is needed.
@router.get("/mixed-policy-spellings", response_model=RecordsPublic)
# ruleid: authz-binding-policy-mismatch
def mixed_policy_spellings(data: Annotated[RecordPage, FromPolicy(OwnerPolicy.page)]) -> RecordPage:
    return data

# A valid binding alongside a wrong one cannot hide the mismatch.
@router.get("/mixed-bindings", response_model=RecordsPublic)
def mixed_bindings(
    # ok: authz-binding-policy-mismatch
    records: Annotated[RecordPage, FromPolicy(RecordPolicy.page)],
    # ruleid: authz-binding-policy-mismatch
    notes: Annotated[RecordNotes, FromPolicy(OwnerOrStaffNotesPolicy.notes)],
):
    return records

# ruleid: authz-policy-override
@router.get("/mixed-override", response_model=RecordNotesPublic, dependencies=[use_policy(NotesPolicy)])
def mixed_override(
    # ok: authz-binding-policy-mismatch
    notes: Annotated[RecordNotes, FromPolicy(NotesPolicy.notes)],
    # ruleid: authz-binding-policy-mismatch
    records: Annotated[RecordPage, FromPolicy(RecordPolicy.page)],
):
    return notes
