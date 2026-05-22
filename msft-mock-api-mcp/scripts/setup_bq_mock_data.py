import os
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

def setup_bigquery_mock():
    client = bigquery.Client()
    dataset_id = os.environ.get("BQ_DATASET")
    if not dataset_id:
        project_id = client.project
        dataset_id = f"{project_id}.ukg_mock_data"
    else:
        project_id = dataset_id.split('.')[0] if '.' in dataset_id else client.project
        
    print(f"Using Google Cloud Project: {project_id}")
    print(f"Using BigQuery Dataset: {dataset_id}")
    
    # Create Dataset if it doesn't exist
    try:
        dataset = client.get_dataset(dataset_id)
        print(f"Dataset {dataset_id} already exists.")
    except NotFound:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {dataset_id}")

    # Define Microsoft Graph User Table Config
    table_name = "microsoft_entra_users"
    table_ref = f"{dataset_id}.{table_name}"
    
    schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("displayName", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("mail", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("mobilePhone", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("userPrincipalName", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("officeLocation", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("jobTitle", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("givenName", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("surname", "STRING", mode="NULLABLE"),
    ]
    
    data = [
        {
            "id": "EMP1001",
            "displayName": "Alex Mercer",
            "mail": "alex.mercer@retail.corp",
            "mobilePhone": "+1-555-019-1001",
            "userPrincipalName": "alex.mercer@retail.corp",
            "officeLocation": "4550",
            "jobTitle": "Senior Sales Associate",
            "givenName": "Alex",
            "surname": "Mercer"
        },
        {
            "id": "EMP1002",
            "displayName": "Sarah Connor",
            "mail": "sarah.connor@retail.corp",
            "mobilePhone": "+1-555-019-1002",
            "userPrincipalName": "sarah.connor@retail.corp",
            "officeLocation": "4550",
            "jobTitle": "Store Manager",
            "givenName": "Sarah",
            "surname": "Connor"
        },
        {
            "id": "EMP1003",
            "displayName": "David Miller",
            "mail": "david.miller@retail.corp",
            "mobilePhone": "+1-555-019-1003",
            "userPrincipalName": "david.miller@retail.corp",
            "officeLocation": "1024",
            "jobTitle": "Sales Associate",
            "givenName": "David",
            "surname": "Miller"
        }
    ]

    # Clean start: Delete table if exists
    client.delete_table(table_ref, not_found_ok=True)
    
    # Create Table
    table = bigquery.Table(table_ref, schema=schema)
    created_table = client.create_table(table)
    print(f"Created table {created_table.table_id}")
    
    # Insert Rows
    errors = client.insert_rows_json(created_table, data)
    if errors == []:
        print(f" Successfully inserted sample Microsoft Graph user rows into {table_name}")
    else:
        print(f"❌ Errors encountered while inserting into {table_name}: {errors}")

if __name__ == "__main__":
    setup_bigquery_mock()
