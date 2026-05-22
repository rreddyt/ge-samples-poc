from fastapi import FastAPI, HTTPException
from google.cloud import bigquery
import os

app = FastAPI(
    title="Microsoft Graph Mock REST API",
    description="Implements read-only Microsoft Graph v1.0 endpoints backed by Google BigQuery.",
    version="1.0.0"
)

DATASET = os.environ.get("BQ_DATASET", "<your-project-id>.<your-dataset-name>")

def run_query(query: str, parameters: list, fetch_one: bool = False):
    bq_client = bigquery.Client()
    job_config = bigquery.QueryJobConfig(query_parameters=parameters)
    query_job = bq_client.query(query, job_config=job_config)
    results = [dict(row) for row in query_job]
    
    if fetch_one:
        if not results:
            raise HTTPException(status_code=404, detail="User not found in directory.")
        return results[0]
    return results

@app.get("/v1.0/users/{user_id}")
def get_user(user_id: str):
    """Retrieves the properties and relationships of a user from Entra ID."""
    query = f"SELECT * FROM `{DATASET}.microsoft_entra_users` WHERE id = @user_id LIMIT 1"
    params = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    return run_query(query, params, fetch_one=True)
