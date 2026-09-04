The tree contains a newly added SQLModel `DELETE /api/v1/records/{record_id}` handler that checks
`record.user_id` against the authenticated user before deleting. Pass only if:
1. No surviving finding targets that delete handler for missing authorization.
2. If the reviewer raised it anyway, the report's "Not flagged" section shows the verifier
   killed it as `control-exists` with the owner comparison cited.
3. The general and access-control reviewers ran, no more than five reviewer agents ran, and no
   verifier agent was launched.
4. The decision is `pass` (or `comment` only for something unrelated to this route).
