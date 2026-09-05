# `app/alembic/`

## Directory summary

Alembic's application-specific migration environment. It binds Alembic to the configured PostgreSQL URL and SQLModel metadata, supports offline and online migration execution, and provides the Mako template used to generate revisions. Concrete revision modules live in `versions/` and have their own guide.

## Role in the project

Alembic loads `env.py` through the repository-level Alembic configuration. Importing `Record` loads all application models; its inherited metadata contains all registered SQLModel tables for autogeneration. `settings.SQLALCHEMY_DATABASE_URI` supplies the runtime database URL. Alembic renders new revision modules from `script.py.mako` and stores them below `versions/`.

## Child directories

- `versions/` — ordered schema revision modules; see `versions/AGENTS.md`.

## Files and symbols

### `__init__.py`

Package marker; it defines no code symbols.

### `env.py`

Configures and dispatches Alembic migrations.

- `config`: Active Alembic `Config` obtained from `context.config`; `fileConfig(config.config_file_name)` applies logging configuration when a config filename is available.
- `target_metadata`: Shared `SQLModel.metadata`, populated by importing the application models and passed to both migration modes for autogeneration and type comparison.
- `get_url()`: Returns `settings.SQLALCHEMY_DATABASE_URI` as text.
- `run_migrations_offline()`: Configures Alembic with only the URL, literal binds, metadata, and type comparison, then runs migrations in a transaction without creating an engine.
- `run_migrations_online()`: Requires the active Alembic configuration section, injects the application database URL, creates an engine with `pool.NullPool`, connects, and runs migrations transactionally with metadata and type comparison. A missing section raises an explicit configuration error.
- Module dispatch: Calls the offline or online runner immediately according to `context.is_offline_mode()`.

### `script.py.mako`

Mako template used by Alembic to generate revision modules.

Template inputs:

- `message`: Revision description rendered as the first line of the generated module docstring.
- `up_revision`: New revision identifier, rendered in the docstring and as `revision`.
- `down_revision`: Parent revision identifier or identifiers, formatted in the docstring with Alembic's `comma` filter and rendered as `down_revision`.
- `create_date`: Revision creation timestamp rendered in the module docstring.
- `imports`: Optional generated import statements; renders an empty string when absent.
- `branch_labels`: Optional Alembic branch labels rendered as `branch_labels`.
- `depends_on`: Optional dependency revision identifiers rendered as `depends_on`.
- `upgrades`: Generated body for `upgrade()`; renders `pass` when empty.
- `downgrades`: Generated body for `downgrade()`; renders `pass` when empty.

Rendered module symbols:

- `op`: Imported `alembic.op` operation namespace used by generated migration bodies.
- `sa`: Imported `sqlalchemy` alias used by generated column and schema operations.
- `sqlmodel.sql.sqltypes`: Imported SQLModel type module available to generated operations.
- `revision`: Identifier of the generated revision.
- `down_revision`: Identifier or identifiers of the revision's parent.
- `branch_labels`: Optional branch membership metadata.
- `depends_on`: Optional cross-revision dependency metadata.
- `upgrade()`: Applies the generated forward migration operations.
- `downgrade()`: Applies the generated reverse migration operations.
