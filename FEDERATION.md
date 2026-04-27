# Federation Refactoring Plan

## Concept

Each memlord server IS a workspace. Users connect multiple servers to their MCP client.
`list_workspaces` returns registered remote (federated) servers.
Calling a tool with `workspace="work"` proxies the request to that server.
Without `workspace`, operates on the local server.

MCP API surface stays identical.

## Steps

### 1. Remove `workspace_id` from `memories`
- Alembic migration: drop `workspace_id` column
- Remove from `Memory` model
- Remove from all queries in `search.py`, `tools/`
- Remove from schemas (`MemoryOut`, etc.)

### 2. Remove `workspaces` table
- Alembic migration: drop `workspaces` table
- Delete `models/workspace.py`
- Remove from `tools/workspaces.py` (list_workspaces, create_workspace, etc.)

### 3. Add `federated_servers` table
- Alembic migration: create table (`id`, `name`, `url`, `token`, `created_at`)
- Add `models/federated_server.py`
- Add `schemas/federated_server.py`

### 4. Rewrite `list_workspaces`
- Returns rows from `federated_servers`
- Optionally include a `"local"` entry representing this server itself

### 5. Add proxy layer
- When `workspace` param is set: look up URL + token from `federated_servers`, forward MCP tool call via HTTP
- When `workspace` is absent or `"local"`: execute locally
- Centralise in `tools/proxy.py` or a decorator

### 6. Simplify all tools
- Drop `workspace` parameter from local query paths
- Remove `workspace_id` filters from all SQL queries

### 7. Update UI
- Remove workspace switcher / workspace management pages
- Add federated servers management page (list, add, delete)

## Error Handling

- `workspace` explicitly specified → server unavailable: raise error (read or write)
- `workspace` not specified (fan-out over all) → server unavailable: skip silently

## Search Across Federated Servers

When `workspace` is not specified:
1. Fire parallel requests: local DB query + one HTTP request per federated server
2. Each source returns top-N results ordered by relevance (already RRF-ranked internally)
3. Merge using RRF over ranks from all sources (scores not needed, only order)
4. Return global top-N

Centralise merge logic in `search.py` as `rrf_merge(ranked_lists) -> list`.

## Out of Scope (for now)
- Sync / replication between servers
- Server discovery / registry
