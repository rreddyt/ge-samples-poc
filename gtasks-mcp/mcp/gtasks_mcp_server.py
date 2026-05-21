import os
from typing import Optional
from mcp.server.fastmcp import FastMCP, Context
import google.auth
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Configure FastMCP server, using host="0.0.0.0" to safely bypass DNS Rebinding Protection on Cloud Run
mcp = FastMCP("Google-Tasks-Agent-MCP", host="0.0.0.0")

def get_tasks_service(ctx: Context):
    """Dynamically instantiates the Google Tasks API client.

    In Cloud Run production (Gemini Enterprise), uses the end-user's OAuth token passed in headers.
    In stdio local development, falls back to Application Default Credentials (ADC).
    """
    request = ctx.request_context.request if ctx.request_context else None
    auth_header = request.headers.get("authorization") if request else None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        creds = Credentials(token=token)
    else:
        # Fallback to ADC for local stdio / playground testing
        creds, _ = google.auth.default(
            scopes=['https://www.googleapis.com/auth/tasks']
        )
    return build('tasks', 'v1', credentials=creds)

@mcp.tool()
async def list_task_lists(ctx: Context) -> list[dict]:
    """Retrieves all task lists belonging to the authenticated user."""
    service = get_tasks_service(ctx)
    results = service.tasklists().list().execute()
    return results.get('items', [])

@mcp.tool()
async def create_task_list(title: str, ctx: Context) -> dict:
    """Creates a new task list for the user.

    Args:
        title: The title of the new task list (e.g., 'Project Milestones').
    """
    service = get_tasks_service(ctx)
    body = {'title': title}
    return service.tasklists().insert(body=body).execute()

@mcp.tool()
async def list_tasks(task_list_id: str, show_completed: bool = True, ctx: Context = None) -> list[dict]:
    """Retrieves all tasks in a specific task list.

    Args:
        task_list_id: The unique identifier of the task list.
        show_completed: If True, returns completed tasks as well. Defaults to True.
    """
    service = get_tasks_service(ctx)
    show_hidden = show_completed
    results = service.tasks().list(
        tasklist=task_list_id,
        showCompleted=show_completed,
        showHidden=show_hidden
    ).execute()
    return results.get('items', [])

@mcp.tool()
async def create_task(
    task_list_id: str,
    title: str,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """Creates a new task inside a specific task list.

    Args:
        task_list_id: The unique identifier of the target task list.
        title: The title of the new task (e.g., 'Schedule sync meeting').
        notes: Optional detailed notes/description of the task.
        due_date: Optional due date in RFC 3339 format (e.g., '2026-06-15T12:00:00Z').
    """
    service = get_tasks_service(ctx)
    body = {'title': title}
    if notes:
        body['notes'] = notes
    if due_date:
        body['due'] = due_date
    return service.tasks().insert(tasklist=task_list_id, body=body).execute()

@mcp.tool()
async def update_task_status(
    task_list_id: str,
    task_id: str,
    completed: bool,
    ctx: Context = None
) -> dict:
    """Updates the status of an existing task to either completed or needsAction.

    Args:
        task_list_id: The unique identifier of the task list.
        task_id: The unique identifier of the task to update.
        completed: If True, marks the task as completed. Otherwise, marks it as needsAction.
    """
    service = get_tasks_service(ctx)
    
    # Fetch existing task details first to preserve other fields during update
    task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
    
    if completed:
        task['status'] = 'completed'
    else:
        task['status'] = 'needsAction'
        task.pop('completed', None)  # Clear completed timestamp if reopening
        
    return service.tasks().update(tasklist=task_list_id, task=task_id, body=task).execute()

@mcp.tool()
async def delete_task(task_list_id: str, task_id: str, ctx: Context = None) -> str:
    """Deletes a specific task from a task list.

    Args:
        task_list_id: The unique identifier of the task list.
        task_id: The unique identifier of the task to delete.
    """
    service = get_tasks_service(ctx)
    service.tasks().delete(tasklist=task_list_id, task=task_id).execute()
    return f"Successfully deleted task '{task_id}' from list '{task_list_id}'."

if __name__ == "__main__":
    import uvicorn
    
    # Use Streamable HTTP if PORT is defined (e.g. Cloud Run) or TRANSPORT is explicitly set
    if os.environ.get("PORT") or os.environ.get("TRANSPORT") in ("sse", "http", "streamable-http"):
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
    else:
        # Fallback to standard stdio transport for local testing and MCP Inspector
        mcp.run(transport="stdio")
