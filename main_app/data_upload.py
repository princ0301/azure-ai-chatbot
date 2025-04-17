import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

def upload_to_azure(files_to_upload):
    """
    Upload files to Azure Blob Storage
    
    Args:
        files_to_upload: Dictionary with local file paths as keys and content types as values
        Example: {"/path/to/file.pdf": "application/pdf", "/path/to/data.csv": "text/csv"}
    """ 
    load_dotenv()
    
    connection_string = os.environ.get("AZURE_CONN_STRING")
    container_name = os.environ.get("AZURE_CONTAINER_NAME")
    
    if not connection_string or not container_name:
        print("Error: Azure connection details not found in environment variables")
        return False
     
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
 
    try:
        container_client.create_container()
        print(f"Created container: {container_name}")
    except Exception:
        print(f"Using existing container: {container_name}")
     
    for local_file, content_type in files_to_upload.items():
        if not os.path.exists(local_file):
            print(f"Warning: File not found - {local_file}")
            continue
            
        blob_name = os.path.basename(local_file)
        try:
            with open(local_file, "rb") as data:
                container_client.upload_blob(
                    name=blob_name,
                    data=data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )
            print(f"✅ Uploaded {blob_name} as {content_type}")
        except Exception as e:
            print(f"Error uploading {blob_name}: {str(e)}")
    
    return True

if __name__ == "__main__": 
    files_to_upload = {
        "./documents/report.pdf": "application/pdf",
        "./data/metrics.csv": "text/csv",
        "./documents/notes.txt": "text/plain"
    }
    
    upload_to_azure(files_to_upload)