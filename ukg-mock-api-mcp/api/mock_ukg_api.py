from fastapi import FastAPI, HTTPException, Query
from google.cloud import bigquery
import os

app = FastAPI(
    title="UKG Pro Mock API",
    description="Implements read-only UKG REST endpoints backed by Google BigQuery.",
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
            raise HTTPException(status_code=404, detail="Resource element not found.")
        return results[0]
    return results

@app.get("/personnel/v1/person-details")
def get_person_details(employee_id: str = Query(..., alias="employeeId")):
    query = f"SELECT * FROM `{DATASET}.person_details` WHERE employeeId = @emp_id LIMIT 1"
    params = [bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id)]
    return run_query(query, params, fetch_one=True)

@app.get("/personnel/v1/employment-details")
def get_employment_details(employee_id: str = Query(..., alias="employeeId")):
    query = f"SELECT * FROM `{DATASET}.employment_details` WHERE employeeId = @emp_id LIMIT 1"
    params = [bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id)]
    return run_query(query, params, fetch_one=True)

@app.get("/personnel/v1/compensation-details")
def get_compensation_details(employee_id: str = Query(..., alias="employeeId")):
    query = f"SELECT * FROM `{DATASET}.compensation_details` WHERE employeeId = @emp_id LIMIT 1"
    params = [bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id)]
    return run_query(query, params, fetch_one=True)

@app.get("/configuration/v1/pay-grades")
def get_pay_grades(job_code: str = Query(None, alias="jobCode")):
    query = f"SELECT * FROM `{DATASET}.pay_grades`"
    params = []
    if job_code:
        query += " WHERE jobCode = @job_code"
        params.append(bigquery.ScalarQueryParameter("job_code", "STRING", job_code))
    return run_query(query, params, fetch_one=False)

@app.get("/configuration/v1/job-profiles")
def get_job_profiles():
    return run_query(f"SELECT * FROM `{DATASET}.job_profiles` WHERE isActive=true", [])

@app.get("/configuration/v1/org-levels")
def get_org_levels():
    return run_query(f"SELECT * FROM `{DATASET}.org_levels` WHERE isActive=true", [])