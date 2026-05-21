import os
import httpx
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GameStop-UKG-Agent-MCP", host="0.0.0.0")

API_BASE_URL = os.environ.get("UKG_API_BASE_URL", "http://localhost:8080")
API_KEY = os.environ.get("UKG_API_KEY", "mock-auth-token-123")

def fetch_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "US-Customer-Api-Key": API_KEY
    }

@mcp.tool()
async def get_employee_employment_profile(employee_id: str) -> dict:
    """Retrieves a store employee's current job title, primary job code, manager name, and active store location number."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{API_BASE_URL}/personnel/v1/employment-details",
            params={"employeeId": employee_id},
            headers=fetch_headers()
        )
        res.raise_for_status()
        return res.json()

@mcp.tool()
async def get_employee_compensation(employee_id: str) -> dict:
    """Retrieves exact compensation markers including hourly base rate, pay frequency, and alphanumeric pay grade assignments."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{API_BASE_URL}/personnel/v1/compensation-details",
            params={"employeeId": employee_id},
            headers=fetch_headers()
        )
        res.raise_for_status()
        return res.json()

@mcp.tool()
async def validate_pay_thresholds(job_code: str) -> list:
    """Provides standard HR-configured payment bounding intervals (minimum and maximum pay rates) assigned to a given job code."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{API_BASE_URL}/configuration/v1/pay-grades",
            params={"jobCode": job_code},
            headers=fetch_headers()
        )
        res.raise_for_status()
        return res.json()

@mcp.tool()
async def get_valid_jobs_and_locations() -> dict:
    """Collects lists of active, permitted corporate Job Profiles and structural store organizational locations."""
    async with httpx.AsyncClient() as client:
        jobs_task = client.get(f"{API_BASE_URL}/configuration/v1/job-profiles", headers=fetch_headers())
        locs_task = client.get(f"{API_BASE_URL}/configuration/v1/org-levels", headers=fetch_headers())
        
        jobs_res, locs_res = await asyncio.gather(jobs_task, locs_task)
        jobs_res.raise_for_status()
        locs_res.raise_for_status()
        
        return {
            "valid_jobs": jobs_res.json(),
            "valid_stores": locs_res.json()
        }
if __name__ == "__main__":
    import uvicorn
    
    # Use Streamable HTTP if PORT is defined (e.g. Cloud Run) or TRANSPORT is explicitly set
    if os.environ.get("PORT") or os.environ.get("TRANSPORT") in ("sse", "http", "streamable-http"):
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
    else:
        # Fallback to standard stdio transport for local testing and MCP Inspector
        mcp.run(transport="stdio")