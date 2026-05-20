import os
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

def setup_bigquery_mock():
    # Initialize the client. It will automatically detect credentials from your 
    # environment (e.g., GOOGLE_APPLICATION_CREDENTIALS or gcloud auth).
    client = bigquery.Client()
    dataset_id = os.environ.get("BQ_DATASET")
    if not dataset_id:
        project_id = client.project
        dataset_id = f"{project_id}.ukg_mock_data"
    else:
        # Extract project ID from full dataset name (e.g. "my-project.dataset")
        project_id = dataset_id.split('.')[0] if '.' in dataset_id else client.project
        
    print(f"Using Google Cloud Project: {project_id}")
    print(f"Using BigQuery Dataset: {dataset_id}")
    
    # 1. Create Dataset if it doesn't exist
    try:
        dataset = client.get_dataset(dataset_id)
        print(f"Dataset {dataset_id} already exists.")
    except NotFound:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"  # Adjust location if needed
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {dataset_id}")

    # 2. Define Table Schemas and Sample Data
    tables_config = {
        "person_details": {
            "schema": [
                bigquery.SchemaField("employeeId", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("firstName", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("lastName", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("email", "STRING", mode="NULLABLE"),
            ],
            "data": [
                {"employeeId": "EMP1001", "firstName": "Alex", "lastName": "Mercer", "email": "amercer@gamestop.com"},
                {"employeeId": "EMP1002", "firstName": "Sarah", "lastName": "Connor", "email": "sconnor@gamestop.com"},
                {"employeeId": "EMP1003", "firstName": "David", "lastName": "Miller", "email": "dmiller@gamestop.com"}
            ]
        },
        "employment_details": {
            "schema": [
                bigquery.SchemaField("employeeId", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("jobTitle", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("primaryJobCode", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("supervisorName", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("orgLevel", "STRING", mode="REQUIRED"), # Store Number
            ],
            "data": [
                {"employeeId": "EMP1001", "jobTitle": "Senior Game Advisor", "primaryJobCode": "SGA01", "supervisorName": "Sarah Connor", "orgLevel": "4550"},
                {"employeeId": "EMP1002", "jobTitle": "Store Leader", "primaryJobCode": "SL01", "supervisorName": "District Manager", "orgLevel": "4550"},
                {"employeeId": "EMP1003", "jobTitle": "Game Advisor", "primaryJobCode": "GA01", "supervisorName": "Sarah Connor", "orgLevel": "1024"}
            ]
        },
        "compensation_details": {
            "schema": [
                bigquery.SchemaField("employeeId", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("hourlyPayRate", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("annualSalary", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("payFrequency", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("payGrade", "STRING", mode="REQUIRED"),
            ],
            "data": [
                {"employeeId": "EMP1001", "hourlyPayRate": 16.50, "annualSalary": 34320.0, "payFrequency": "Hourly", "payGrade": "GRADE_B"},
                {"employeeId": "EMP1002", "hourlyPayRate": 26.00, "annualSalary": 54080.0, "payFrequency": "Hourly", "payGrade": "GRADE_D"},
                {"employeeId": "EMP1003", "hourlyPayRate": 14.00, "annualSalary": 29120.0, "payFrequency": "Hourly", "payGrade": "GRADE_A"}
            ]
        },
        "pay_grades": {
            "schema": [
                bigquery.SchemaField("jobCode", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("payGrade", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("minimumPayRate", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("maximumPayRate", "FLOAT", mode="REQUIRED"),
            ],
            "data": [
                {"jobCode": "GA01", "payGrade": "GRADE_A", "minimumPayRate": 13.00, "maximumPayRate": 15.50},
                {"jobCode": "SGA01", "payGrade": "GRADE_B", "minimumPayRate": 15.00, "maximumPayRate": 19.00},
                {"jobCode": "ASL01", "payGrade": "GRADE_C", "minimumPayRate": 18.50, "maximumPayRate": 23.00},
                {"jobCode": "SL01", "payGrade": "GRADE_D", "minimumPayRate": 22.00, "maximumPayRate": 32.00}
            ]
        },
        "job_profiles": {
            "schema": [
                bigquery.SchemaField("jobCode", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("jobTitle", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("isActive", "BOOLEAN", mode="REQUIRED"),
            ],
            "data": [
                {"jobCode": "GA01", "jobTitle": "Game Advisor", "isActive": True},
                {"jobCode": "SGA01", "jobTitle": "Senior Game Advisor", "isActive": True},
                {"jobCode": "ASL01", "jobTitle": "Assistant Store Leader", "isActive": True},
                {"jobCode": "SL01", "jobTitle": "Store Leader", "isActive": True}
            ]
        },
        "org_levels": {
            "schema": [
                bigquery.SchemaField("orgLevel", "STRING", mode="REQUIRED"), # Store Number
                bigquery.SchemaField("storeName", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("isActive", "BOOLEAN", mode="REQUIRED"),
            ],
            "data": [
                {"orgLevel": "4550", "storeName": "GameStop - Austin Central", "isActive": True},
                {"orgLevel": "1024", "storeName": "GameStop - Dallas North", "isActive": True},
                {"orgLevel": "2048", "storeName": "GameStop - Houston West", "isActive": True}
            ]
        }
    }

    # 3. Execution Loop
    for table_name, config in tables_config.items():
        table_ref = f"{dataset_id}.{table_name}"
        
        # Delete table if it exists to clean start and avoid duplicate inserts
        client.delete_table(table_ref, not_found_ok=True)
        
        # Build Table Object
        table = bigquery.Table(table_ref, schema=config["schema"])
        created_table = client.create_table(table)
        print(f"Created table {created_table.table_id}")
        
        # Populate Table
        errors = client.insert_rows_json(created_table, config["data"])
        if errors == []:
            print(f" Successfully inserted sample rows into {table_name}")
        else:
            print(f"❌ Errors encountered while inserting into {table_name}: {errors}")

if __name__ == "__main__":
    setup_bigquery_mock()