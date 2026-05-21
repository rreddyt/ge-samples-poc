import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Stdio server parameters to launch your Google Tasks MCP server
    server_params = StdioServerParameters(
        command="./.venv/bin/python",
        args=["mcp/gtasks_mcp_server.py"],
        env=os.environ
    )
    
    print("🚀 Connecting to local Google Tasks MCP Server...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ Connected & Initialized successfully!\n")
                
                # 1. List available tools
                print("🧰 Listing Registered Tools:")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                for tool in tools:
                    print(f"  - \033[1m{tool.name}\033[0m: {tool.description}")
                print()
                
                # 2. Call list_task_lists
                print("🧪 Calling tool 'list_task_lists' (Using Local Application Default Credentials)...")
                result = await session.call_tool("list_task_lists", {})
                print("Response from server:")
                print(f"\033[32m{result.content[0].text}\033[0m\n")

    except Exception as e:
        print(f"❌ Error during local Google Tasks MCP test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
