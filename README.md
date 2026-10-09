# Events Aggregator

## Database migrations

Create the schema in the configured PostgreSQL database:

```bash
uv run alembic upgrade head
```

After changing ORM models, create a migration and apply it:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
```

The database connection is read from the application settings and `.env` file.