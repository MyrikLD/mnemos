from fastmcp import FastMCP

from mnemos.tools import (
    delete,
    health,
    list_memories,
    recall,
    retrieve,
    search_by_tag,
    store,
)

mcp: FastMCP = FastMCP("Mnemos")

mcp.mount(store)
mcp.mount(retrieve)
mcp.mount(recall)
mcp.mount(list_memories)
mcp.mount(search_by_tag)
mcp.mount(delete)
mcp.mount(health)
