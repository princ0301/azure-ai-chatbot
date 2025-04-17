import os
import tempfile
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

def download_from_azure():
    """Download files from Azure Blob Storage to a temporary directory""" 
    load_dotenv()
    
    conn_str = os.environ.get("AZURE_CONN_STRING")
    container_name = os.environ.get("AZURE_CONTAINER_NAME")
    
    if not conn_str or not container_name:
        print("Error: Azure connection details not found in environment variables")
        return None
      
    temp_dir = tempfile.mkdtemp()
    
    try: 
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service.get_container_client(container_name)
 
        downloaded_files = []
        for blob in container_client.list_blobs():
            file_path = os.path.join(temp_dir, blob.name)
             
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
             
            with open(file_path, "wb") as f:
                f.write(container_client.download_blob(blob).readall())
            
            downloaded_files.append(file_path)
        
        print(f"✅ Downloaded {len(downloaded_files)} files from Azure")
        return temp_dir, downloaded_files
    
    except Exception as e:
        print(f"Error downloading from Azure: {str(e)}")
        return None, []

if __name__ == "__main__":
    temp_dir, files = download_from_azure()
    if files:
        print(f"Files downloaded to: {temp_dir}")
        for file in files:
            print(f"- {os.path.basename(file)}")