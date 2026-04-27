import asyncio

from fastmcp import Client
from fastmcp.client import StdioTransport

transport = StdioTransport(
    command="python",
    args=["src/memlord/main.py", "--stdio"],
    env={
        "MEMLORD_STDIO_USER_ID": "1",
    },
)

# Local Python script
client = Client(transport)


async def main():
    async with client:
        # Basic server interaction
        await client.ping()

        # List available operations
        tools = await client.list_tools()
        print([i.name for i in tools])

        # Execute operations
        result = await client.call_tool("list_memories")
        print(result)

        # result = await client.call_tool("get_memory", {"name": "5"})
        # print(result)


if __name__ == "__main__":
    asyncio.run(main())
