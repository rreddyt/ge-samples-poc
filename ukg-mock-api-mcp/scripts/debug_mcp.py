import asyncio
import os
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="./.venv/bin/python",
        args=["mcp/mock_ukg_mcp_server.py"],
        env=os.environ
    )
    
    print("🚀 Debugging local UKG MCP Server...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected!")
                
                # Call validate_pay_thresholds for GA01
                try:
                    print("\n🧪 Calling validate_pay_thresholds('GA01')...")
                    res = await session.call_tool("validate_pay_thresholds", {"job_code": "GA01"})
                    print("Success! Response content:")
                    print(res.content)
                except Exception as e:
                    print("❌ Exception in validate_pay_thresholds:")
                    traceback.print_exc()
                    
                # Call get_valid_jobs_and_locations
                try:
                    print("\n🧪 Calling get_valid_jobs_and_locations()...")
                    res = await session.call_tool("get_valid_jobs_and_locations", {})
                    print("Success! Response content:")
                    print(res.content)
                except Exception as e:
                    print("❌ Exception in get_valid_jobs_and_locations:")
                    traceback.print_exc()

    except Exception as e:
        print("❌ Connection-level Exception:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
