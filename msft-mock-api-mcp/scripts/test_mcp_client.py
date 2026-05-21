import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Verify environment
    api_url = os.environ.get("MSFT_API_BASE_URL")
    if not api_url:
        print("⚠️  WARNING: MSFT_API_BASE_URL environment variable is not set. Local calls might fail.")
    else:
        print(f"🔗 Using API Base: {api_url}")

    # Stdio server parameters to launch your mock server
    server_params = StdioServerParameters(
        command="./.venv/bin/python",
        args=["mcp/mock_msft_mcp_server.py"],
        env=os.environ
    )
    
    print("🚀 Connecting to local MSFT Graph MCP Server...")
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
                
                # 2. Call get_entra_user_details
                target_emp = "EMP1001"
                print(f"🧪 Calling tool 'get_entra_user_details' for employee_id '{target_emp}'...")
                result = await session.call_tool("get_entra_user_details", {"employee_id": target_emp})
                print("Response from server:")
                print(f"\033[32m{result.content[0].text}\033[0m\n")

    except Exception as e:
        print(f"❌ Error during local MCP test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
