FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY api/ ./api/
COPY mcp/ ./mcp/

EXPOSE 8080

# Default execution targets the FastMCP server app
CMD ["python", "mcp/mock_msft_mcp_server.py"]
