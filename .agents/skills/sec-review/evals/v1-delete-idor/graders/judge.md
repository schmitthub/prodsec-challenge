The tree contains a newly added SQLModel `DELETE /api/v1/records/{record_id}` handler that
deletes a record after checking only that it exists, with no comparison of `record.user_id`
to the authenticated user. Pass only if all hold:
1. The report contains a finding on that delete handler describing the missing owner or
   role check, at severity high or critical.
2. The general and access-control reviewers ran, no more than five reviewer agents ran, and
   no verifier agent was launched.
3. The finding's evidence is deterministic: an inline reproduction (for example a member
   deleting another member's record) or a failing test, not reasoning alone.
4. No finding targets `GET /api/v1/records/{record_id}/notes`, which has a correct owner check.
5. The fix direction names a control to add (owner comparison or an owner-bound query) and
   contains no code.
