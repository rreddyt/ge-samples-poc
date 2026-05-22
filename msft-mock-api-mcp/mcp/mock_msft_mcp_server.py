import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Retail-Microsoft-Agent-MCP", host="0.0.0.0")

API_BASE_URL = os.environ.get("MSFT_API_BASE_URL", "http://localhost:8081")
API_KEY = os.environ.get("MSFT_API_KEY", "mock-auth-token-123")

def fetch_headers():
    return {
        "Authorization": f"Bearer {API_KEY}"
    }

@mcp.tool()
async def get_entra_user_details(employee_id: str) -> dict:
    """Simulates querying Microsoft Entra ID via Graph API to retrieve employee directory details.

    Use this to pre-populate employee details (displayName, mail, mobilePhone, officeLocation, jobTitle)
    using their Employee ID in real-time (< 3 seconds).
    """
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{API_BASE_URL}/v1.0/users/{employee_id}",
            headers=fetch_headers()
        )
        res.raise_for_status()
        return res.json()

if __name__ == "__main__":
    import uvicorn
    
    # Use Streamable HTTP if PORT is defined (e.g. Cloud Run) or TRANSPORT is explicitly set
    if os.environ.get("PORT") or os.environ.get("TRANSPORT") in ("sse", "http", "streamable-http"):
        port = int(os.environ.get("PORT", 8081))
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
    else:
        # Fallback to standard stdio transport for local testing and MCP Inspector
        mcp.run(transport="stdio")
