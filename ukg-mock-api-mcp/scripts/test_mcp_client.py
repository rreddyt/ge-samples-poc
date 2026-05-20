import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Verify environment
    api_url = os.environ.get("UKG_API_BASE_URL")
    if not api_url:
        print("⚠️  WARNING: UKG_API_BASE_URL environment variable is not set. Local calls might fail.")
    else:
        print(f"🔗 Using API Base: {api_url}")

    # Stdio server parameters to launch your mock server
    server_params = StdioServerParameters(
        command="./.venv/bin/python",
        args=["mcp/mock_ukg_mcp_server.py"],
        env=os.environ
    )
    
    print("🚀 Connecting to local UKG MCP Server...")
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
                
                # 2. Call validate_pay_thresholds
                target_job = "MGR"
                print(f"🧪 Calling tool 'validate_pay_thresholds' for jobCode '{target_job}'...")
                result = await session.call_tool("validate_pay_thresholds", {"job_code": target_job})
                print("Response from server:")
                print(f"\033[32m{result.content[0].text}\033[0m\n")
                
                # 3. Call get_valid_jobs_and_locations
                print("🧪 Calling tool 'get_valid_jobs_and_locations'...")
                result = await session.call_tool("get_valid_jobs_and_locations", {})
                print("Response from server:")
                # Print snippet of results to keep it readable
                text = result.content[0].text
                print(f"\033[32m{text[:300]}...\033[0m\n")

    except Exception as e:
        print(f"❌ Error during local MCP test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
