# Mnemos

MCP memory server with hybrid BM25 + semantic search.

## Features

- **Hybrid search** — BM25 (FTS5) + vector KNN (sqlite-vec) fused via Reciprocal Rank Fusion
- **7 MCP tools** — store, retrieve, recall, list, search by tag, delete, health check
- **Web UI** — browse, search, edit and delete memories in the browser
- **OAuth 2.1** — optional, full in-process authorization server
- **Zero external services** — everything in a single SQLite file

## Quickstart

```bash
# Install dependencies
uv sync --dev

# Download ONNX model (~23 MB)
uv run python scripts/download_model.py

# Run migrations
alembic upgrade head

# Start the server
mnemos
```

Open **http://localhost:8000** for the Web UI. The MCP endpoint is at `/mcp`.

## Docker

```bash
cp .env.example .env
docker compose up
```

## Configuration

All settings use the `MNEMOS_` prefix. See [`.env.example`](.env.example) for the full list.

| Variable                  | Default               | Description                  |
|---------------------------|-----------------------|------------------------------|
| `MNEMOS_DB_PATH`          | `/data/memory.db`     | SQLite database path         |
| `MNEMOS_PORT`             | `8000`                | Server port                  |
| `MNEMOS_BASE_URL`         | —                     | Public URL (required for OAuth) |
| `MNEMOS_OAUTH_JWT_SECRET` | —                     | Enables OAuth when set       |
| `MNEMOS_OAUTH_PASSWORD`   | —                     | Login page password          |

OAuth is enabled only when `MNEMOS_BASE_URL`, `MNEMOS_OAUTH_JWT_SECRET`, and `MNEMOS_OAUTH_PASSWORD` are all set.

## MCP Tools

| Tool                   | Description                                      |
|------------------------|--------------------------------------------------|
| `store_memory`         | Save a memory (idempotent by content)            |
| `retrieve_memory`      | Hybrid semantic + full-text search               |
| `recall_memory`        | Search by natural-language time expression       |
| `list_memories`        | Paginated list with type/tag filters             |
| `search_by_tag`        | AND/OR tag search                                |
| `delete_memory`        | Delete by ID                                     |
| `check_database_health`| DB stats and extension status                    |

## Development

```bash
pyright src/        # type check
black src/          # format
pytest              # run tests
alembic-autogen-check  # verify migrations are up to date
```
