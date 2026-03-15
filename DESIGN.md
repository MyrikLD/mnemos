# Mnemos — Design Document

## Overview

MCP server for storing and searching memory. Hybrid search: BM25 (full-text) + vector (semantic similarity) combined via Reciprocal Rank Fusion.

## Stack

| Component            | Library                                             |
|----------------------|-----------------------------------------------------|
| MCP framework        | `fastmcp >= 3.1.0` — standalone server              |
| UI                   | `fastapi[all]`                                      |
| Database             | SQLite (aiosqlite + SQLAlchemy async)               |
| Migrations           | `alembic` + `alembic-autogen-check` (dev)           |
| Vector store         | `sqlite-vec`                                        |
| Full-text search     | SQLite FTS5 (built-in, BM25)                        |
| Embeddings           | `onnxruntime` + `all-MiniLM-L6-v2.onnx` (384 dims) |
| Tokenization         | `tokenizers`                                        |
| Time parsing         | `dateparser`                                        |
| Model                | ONNX files excluded from git, downloaded via script |
| Configuration        | `pydantic-settings`                                 |
| Auth                 | OAuth 2.1 — custom `OAuthProvider` (fastmcp)        |
| Deployment           | Docker + docker-compose                             |

## Dependencies

**production:** `aiosqlite`, `alembic`, `authlib`, `fastapi[all]`, `fastmcp`, `onnxruntime`, `pydantic-settings`, `dateparser`, `sqlite-vec`, `sqlalchemy`, `tokenizers`

**dev:** `alembic-autogen-check`, `black`, `httpx`, `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `pytest-xdist`

## Project Structure

```
src/mnemos/
├── __init__.py
├── main.py                # entrypoint: FastAPI app + uvicorn
├── server.py              # FastMCP("Mnemos") + mcp.mount() per tool
├── config.py              # pydantic-settings (MNEMOS_* prefix)
├── db.py                  # async SQLAlchemy engine + sqlite-vec loader + MCPSessionDep/APISessionDep
├── embeddings.py          # ONNX session, tokenization, mean pooling, L2 norm
├── search.py              # hybrid BM25 + vector KNN + RRF fusion
├── oauth.py               # custom OAuthProvider (fastmcp.server.auth)
├── ui.py                  # FastAPI UI routes
├── models/
│   ├── __init__.py        # re-exports only
│   ├── base.py            # SQLAlchemy Base + naming convention
│   ├── memory.py          # Memory table
│   ├── tag.py             # Tag table
│   ├── memory_tag.py      # MemoryTag M2M table
│   ├── oauth_client.py    # OAuthClient table
│   └── schema_version.py  # SchemaVersion table
├── schemas/
│   ├── __init__.py        # re-exports only
│   ├── memory_type.py     # MemoryType StrEnum
│   ├── search.py          # SearchResult, MemoryResult
│   ├── store.py           # StoreResult
│   ├── recall.py          # RecallResult
│   ├── list_memories.py   # MemoryListItem, MemoryPage
│   ├── delete.py          # DeleteResult
│   ├── update.py          # UpdateMemoryRequest
│   └── health.py          # HealthResult
├── dao/
│   ├── __init__.py        # re-exports MemoryDao
│   └── memory.py          # MemoryDao — DB access layer for memories
├── templates/             # Jinja2 templates (base, index, search, memory)
├── onnx/
│   ├── model.onnx         # all-MiniLM-L6-v2 (excluded from git, see scripts/)
│   └── tokenizer.json     # (excluded from git, see scripts/)
└── tools/
    ├── __init__.py        # re-exports: mcp instances as named aliases
    ├── store.py           # store_memory → StoreResult
    ├── retrieve.py        # retrieve_memory → list[MemoryResult]
    ├── recall.py          # recall_memory → list[RecallResult]
    ├── list_memories.py   # list_memories → MemoryPage
    ├── get_memory.py      # get_memory → MemoryListItem
    ├── search_by_tag.py   # search_by_tag → list[MemoryListItem]
    ├── delete.py          # delete_memory → DeleteResult
    └── health.py          # check_database_health → HealthResult
scripts/
└── download_model.py      # download model.onnx + tokenizer.json from HuggingFace
migrations/                # Alembic
├── env.py                 # sync engine (aiosqlite doesn't support enable_load_extension)
├── script.py.mako
└── versions/
alembic.ini
Dockerfile
docker-compose.yml
.env.example
```

---

## Configuration

Via `pydantic-settings`. Sources in priority order: environment variables (prefix `MNEMOS_`) → `.env` file → defaults.

| Variable                  | Default                  | Description                        |
|---------------------------|--------------------------|------------------------------------|
| `MNEMOS_DB_PATH`          | `/data/memory.db`        | Path to SQLite file (volume)       |
| `MNEMOS_MODEL_DIR`        | `/app/src/mnemos/onnx`   | Directory containing ONNX model    |
| `MNEMOS_HOST`             | `0.0.0.0`                | uvicorn host                       |
| `MNEMOS_PORT`             | `8000`                   | uvicorn port                       |
| `MNEMOS_BASE_URL`         | —                        | Public server URL                  |
| `MNEMOS_RRF_K`            | `60`                     | RRF fusion k parameter             |
| `MNEMOS_DEFAULT_LIMIT`    | `10`                     | Default result limit               |
| `MNEMOS_SIM_THRESHOLD`    | `0.7`                    | Default cosine similarity threshold|
| `MNEMOS_OAUTH_JWT_SECRET` | —                        | JWT signing secret                 |
| `MNEMOS_PASSWORD`   | —                        | Login page password                |

---

## Embeddings Pipeline

`content` → tokenization (`tokenizer.json`) → ONNX inference → mean pooling (with attention mask) → L2 normalize → `float32[384]` → sqlite-vec

Model files: `src/mnemos/onnx/model.onnx`, `src/mnemos/onnx/tokenizer.json` — excluded from git. Download before running: `uv run python scripts/download_model.py` (source: HuggingFace `sentence-transformers/all-MiniLM-L6-v2`).

---

## Database Schema

**oauth_clients** — OAuth client registrations: `client_id` (PK), `data` (JSON — full client metadata), `created_at`

**memories** — main table: `id` (PK, stable public identifier), `content` (UNIQUE — idempotency), `memory_type`, `metadata` (JSON), `created_at`

**memories_fts** — FTS5 virtual table, kept in sync with `memories` via triggers (INSERT/UPDATE/DELETE). Tokenizer: `porter unicode61`. Used for BM25 search.

**memories_vec** — sqlite-vec virtual table: `memory_id` (PK, FK → `memories.id`), `embedding FLOAT[384]`. Used for KNN search.

**tags** — `id`, `name` (UNIQUE, NOCASE)

**memory_tags** — M2M: `memory_id` → `memories.id` (CASCADE), `tag_id` → `tags.id` (CASCADE)

**schema_version** — `version INTEGER`, `applied_at DATETIME`. Used in `check_database_health`.

---

## Hybrid Search: BM25 + Vector + RRF

### Algorithm

1. Run two queries in parallel:
   - **BM25**: FTS5 `MATCH`, return top-N with BM25 score
   - **Vector**: sqlite-vec KNN, return top-N with cosine distance (similarity = 1 - distance)
2. Compute RRF score: `rrf(d) = 1 / (k + rank_bm25(d)) + 1 / (k + rank_vector(d))`, where `k = 60`. If a document appears in only one list, the other term is 0.
3. Sort by descending `rrf_score`, return top-`limit`.

### Usage in tools

| Tool              | BM25 | Vector | RRF                           |
|-------------------|------|--------|-------------------------------|
| `retrieve_memory` | ✅   | ✅     | ✅                             |
| `recall_memory`   | ✅   | ✅     | ✅ (+ date filter)             |
| `search_by_tag`   | —    | —      | — (tag filter only)           |
| `list_memories`   | —    | —      | — (date sort only)            |
| `get_memory`      | —    | —      | — (ID lookup only)            |

---

## MCP Tools

### `store_memory`

Save a new memory entry.

| Field             | Type     | Required | Description                             |
|-------------------|----------|----------|-----------------------------------------|
| `content`         | string   | ✅        | Memory text                             |
| `memory_type`     | string   | ❌        | Type: see `MemoryType` enum below       |
| `tags`            | string[] | ❌        | Tags                                    |
| `metadata`        | object   | ❌        | Arbitrary metadata (JSON)               |

**MemoryType enum:** `observation`, `feedback`, `fact`, `preference`, `instruction`, `task`, `plan`

**Logic:** UNIQUE on `content` → idempotent (if content already exists, return existing) → INSERT RETURNING → embedding → `memories_vec` (raw SQL, vec0 has no triggers) → tags via `sqlite_insert(...).on_conflict_do_nothing()` → FTS5 via trigger.

**Returns:** `StoreResult` — `id`, `created_at`, `created` (bool — new or already existed).

---

### `retrieve_memory`

Hybrid semantic + full-text search.

| Field                  | Type    | Default | Description                             |
|------------------------|---------|---------|-----------------------------------------|
| `query`                | string  | —       | Search query                            |
| `limit`                | integer | 10      | Max number of results                   |
| `similarity_threshold` | float   | 0.7     | Minimum cosine similarity (0.0–1.0)     |

**Logic:** BM25 + vector → RRF → similarity threshold filter → top-`limit`.

**Returns:** `list[MemoryResult]` — `id`, `content`, `memory_type`, `tags`, `metadata`, `created_at`, `rrf_score`.

---

### `recall_memory`

Time-based + semantic search in natural language.

| Field       | Type    | Default | Description                                                       |
|-------------|---------|---------|-------------------------------------------------------------------|
| `query`     | string  | —       | Query: `"last week"`, `"yesterday"`, `"about Python last month"`  |
| `n_results` | integer | 5       | Max number of results                                             |

**Logic:** `dateparser` extracts temporal expression → filter `created_at BETWEEN date_from AND date_to` → hybrid search on the remaining query. If no time expression found — plain hybrid search.

**Returns:** `list[RecallResult]` — `id`, `content`, `memory_type`, `tags`, `created_at`.

---

### `list_memories`

Paginated list with filtering.

| Field         | Type    | Default | Description                  |
|---------------|---------|---------|------------------------------|
| `page`        | integer | 1       | Page number (1-based)        |
| `page_size`   | integer | 10      | Page size (max 100)          |
| `memory_type` | string  | ❌       | Filter by type               |
| `tag`         | string  | ❌       | Filter by tag                |

**Logic:** SELECT with LIMIT/OFFSET, sorted by `created_at DESC`.

**Returns:** `MemoryPage` — `items: list[MemoryListItem]`, `total`, `page`, `page_size`, `total_pages`.

---

### `search_by_tag`

Tag search with boolean logic.

| Field       | Type         | Default | Description              |
|-------------|--------------|---------|--------------------------|
| `tags`      | string[]     | —       | Tags to search           |
| `operation` | `AND` / `OR` | `AND`   | Tag combination logic    |

**Logic:** `AND` — all tags present; `OR` — at least one.

**Returns:** `list[MemoryListItem]` — `id`, `content`, `memory_type`, `tags`, `created_at`.

---

### `get_memory`

Fetch a single memory by ID with full details.

| Field | Type    | Description |
|-------|---------|-------------|
| `id`  | integer | Entry ID    |

**Returns:** `MemoryListItem` — `id`, `content`, `memory_type`, `tags`, `metadata`, `created_at`.

---

### `delete_memory`

Delete an entry by ID.

| Field | Type    | Description |
|-------|---------|-------------|
| `id`  | integer | Entry ID    |

**Logic:** DELETE from `memories_vec` (raw SQL, vec0 has no FK CASCADE) → DELETE from `memories` RETURNING id (CASCADE → `memory_tags`) → FTS5 via trigger. If not found — `ValueError`.

**Returns:** `DeleteResult` — `success: bool`, `id`.

---

### `check_database_health`

Database status. No parameters.

**Returns:** `HealthResult` — `status`, `total_memories`, `db_path`, `db_size_bytes`, `schema_version`, `vec_extension`, `fts_ok`.

---

## Deployment

Run via **Docker** only, single container, single uvicorn process.

**Architecture:** FastAPI is the main ASGI app. MCP server is mounted via `app.mount("/", mcp.http_app(path="/mcp"))`. Single port, single entrypoint.

```
FastAPI (/)
├── /          — Web UI (list, search, view, edit, delete)
└── /mcp       — MCP HTTP/SSE (fastmcp)
    ├── /login     — OAuth login page
    ├── /authorize — OAuth 2.1 authorization endpoint
    ├── /token     — OAuth 2.1 token endpoint
    ├── /register  — Dynamic Client Registration
    └── /revoke    — Token revocation
```

Dockerfile: multi-stage build, `python:3.12-slim`, uv for dependencies. Configuration via `.env`.

## Authentication

OAuth 2.1 — `MnemosOAuthProvider(OAuthProvider)` in `oauth.py`, full in-process Authorization Server.

**Mechanism:**
- `authorize()` → saves `_PendingAuth` → redirect to `/login?id=<pending_id>`
- `/login` GET — HTML password form; POST — `secrets.compare_digest` → auth code → redirect to `redirect_uri`
- JWT access + refresh tokens: `JWTIssuer` (HS256, key derived via HKDF from `jwt_secret`)
- Access tokens stored in-memory by JTI (`_access_tokens[jti]`) — verification: JWT decode → jti lookup
- Refresh tokens stored in-memory by raw token string
- Token rotation on `exchange_refresh_token` — old pair revoked via `_revoke_pair`
- Dynamic Client Registration enabled (scope: `mcp`, default: `mcp`)
- Token revocation via `_revoke_pair`: removes from `_access_tokens` / `_refresh_tokens` and the paired token

OAuth is enabled only when all three are set: `MNEMOS_OAUTH_JWT_SECRET`, `MNEMOS_PASSWORD`, `MNEMOS_BASE_URL`. If any one is missing — server starts without authentication.

---

## Web UI (FastAPI)

Web interface over the same database. Stack: FastAPI + Jinja2 (server-side rendering) + HTMX (dynamic updates without full page reload).

| Section | Description                                                      |
|---------|------------------------------------------------------------------|
| List    | Paginated list of entries, filter by type and tag               |
| Search  | Hybrid search (BM25 + vector) by text                           |
| View    | Detail card: content, tags, metadata, date                      |
| Edit    | Modify `content`, `memory_type`, `tags`, `metadata`             |
| Delete  | Delete with confirmation                                        |

**API endpoints:** `GET /`, `GET /search?q=...`, `GET /memory/{id}`, `PUT /memory/{id}`, `DELETE /memory/{id}`

---

## FastMCP Tool Conventions

- Each tool file has its own `mcp = FastMCP()`, tool registered via `@mcp.tool`
- `server.py` mounts all sub-servers via `mcp.mount()`
- Sessions: `MCPSessionDep` (for MCP tools) and `APISessionDep` (for FastAPI routes) from `mnemos.db`; parameter typed as `s: AsyncSession = MCPSessionDep  # type: ignore[assignment]`
- DB access via `MemoryDao(s)` from `mnemos.dao` — tool files do not execute queries directly
- Commit/rollback managed by `session_dep` — never call manually
- `output_schema=Model.model_json_schema()` — only for tools returning an object; list-returning tools use bare `@mcp.tool` (MCP spec does not allow array as output_schema)
- SQLAlchemy Core: `select()`, `insert()`, `delete()`, `update()`. `sa.text()` only for sqlite-specific syntax (vec0, FTS5). `.mappings().all()` for multi-column results
