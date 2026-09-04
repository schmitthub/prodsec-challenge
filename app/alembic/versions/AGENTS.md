# `app/alembic/versions/`

## Directory summary

Versioned Alembic schema migrations for the records service. This directory currently contains the base revision that creates the PostgreSQL tables backing users, records, and record notes. Revision modules are executable migration history: keep their identifiers and dependency chain stable, and add a later revision for subsequent schema changes instead of rewriting an applied migration.

## Role in the project

Alembic discovers these modules through the parent migration environment's script location. Each revision exposes metadata identifying its place in the graph plus forward and reverse operations that run through `alembic.op`. The operations here must remain consistent with the SQLModel tables in `app.models`, while later schema changes should be represented by new child revisions.

## Files and symbols

### `49e1c89cd1bb_init_users_records_record_notes.py`

Initial schema revision for users, records, and record notes.

- `sa`: Imported `sqlalchemy` module alias used for columns, UUIDs, enums, keys, and constraints.
- `sqlmodel`: Package name bound by importing `sqlmodel.sql.sqltypes`; its `AutoString` type renders model string fields into the migration.
- `op`: Alembic operations namespace used to create and drop tables and indexes.
- `revision`: Revision identifier `49e1c89cd1bb`.
- `down_revision`: `None`, marking this as the base revision.
- `branch_labels`: `None`; the revision belongs to no named branch.
- `depends_on`: `None`; it has no extra dependency revision.
- `upgrade()`: Applies the base schema in dependency order:
  - Creates `user` with required `email` (`AutoString(255)`), `role` (`AutoString(50)`), UUID `id`, and `hashed_password`; `id` is the primary key and the separately created `ix_user_email` index enforces unique emails.
  - Creates the named PostgreSQL enum types `recordtype` (`lab_result`) and `recordstatus` (`released`) as part of creating `record`. The table has required enum `type` and `status`, nullable `summary` (`AutoString(255)`), UUID primary key `id`, and required UUID `user_id`; `user_id` references `user.id` with cascading deletes, and `unique_user_record_summary` covers `(user_id, summary)`.
  - Creates `recordnote` with required `note` (`AutoString(255)`), UUID primary key `id`, and required UUID `record_id`; `record_id` references `record.id` with cascading deletes, and `unique_record_note` covers `(record_id, note)`.
- `downgrade()`: Drops `recordnote` and `record` before their referenced `user` table, explicitly drops `ix_user_email`, then drops `user`. It does not explicitly drop the named `recordtype` or `recordstatus` PostgreSQL enum types, so those types can remain after downgrade.
