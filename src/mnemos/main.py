from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from mnemos.config import settings
from mnemos.server import mcp
from mnemos.ui import router as ui_router

mcp_app = mcp.http_app(path="/mcp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.lifespan(mcp_app):
        yield


app = FastAPI(title="Mnemos", lifespan=lifespan)
# UI routes must be registered BEFORE the root mount so they take priority.
app.include_router(ui_router)
# Mount mcp_app at "/" so that OAuth /.well-known/* endpoints are at the root,
# matching what MCP clients expect.  The MCP transport itself is at /mcp.
app.mount("/", mcp_app)


def main() -> None:
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
