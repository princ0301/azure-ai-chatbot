import streamlit as st
import os
from dotenv import load_dotenv
import tempfile
import mimetypes

# Import backend modules
from chat_app import ChatBackend
from data_download import download_from_azure
from data_upload import upload_to_azure
 
css = '''
<style>
.chat-message {
    padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
}
.chat-message.user {
    background-color: #2b313e
}
.chat-message.bot {
    background-color: #475063
}
.chat-message .avatar {
  width: 20%;
}
.chat-message .avatar img {
  max-width: 78px;
  max-height: 78px;
  border-radius: 50%;
  object-fit: cover;
}
.chat-message .message {
  width: 80%;
  padding: 0 1.5rem;
  color: #fff;
}
/* Fixed bottom bar styles */
.bottom-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #ffffff;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
    z-index: 1000;
}
.main-content {
    margin-bottom: 100px; /* Add space for fixed bottom bar */
}
</style>
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://i.ibb.co/cN0nmSj/Screenshot-2023-05-28-at-02-37-21.png" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://i.ibb.co/rdZC7LZ/Photo-logo-1.png">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''

def handle_user_input(user_question, chat_backend):
    if not st.session_state.data_processed:
        st.warning("Please connect to Azure and process data first")
        return
    
    with st.spinner("Searching your data..."):
        response = chat_backend.ask_question(user_question)
        
        if "error" in response:
            st.error(response["error"])
            return
     
    chat_history = response.get("chat_history", [])
    for i, message in enumerate(chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
     
    source_docs = response.get("source_documents", [])
    if source_docs:
        with st.expander("Sources"):
            for i, doc in enumerate(source_docs):
                st.write(f"**Source {i+1}**")
                st.write(doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content)
                st.write("---")

def get_mimetype(file_path):
    """Get the mimetype for a file"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        # Fallback mime types for common file extensions
        ext = os.path.splitext(file_path)[1].lower()
        fallback_types = {
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.html': 'text/html'
        }
        mime_type = fallback_types.get(ext, 'application/octet-stream')
    return mime_type

def main():
    load_dotenv()
    mimetypes.init()
     
    st.set_page_config(
        page_title="Azure Data Chat Assistant",
        page_icon="☁️",
        layout="wide"
    )
    
    st.write(css, unsafe_allow_html=True)
     
    # Initialize session state variables
    if "data_processed" not in st.session_state:
        st.session_state.data_processed = False
    if "connected_to_azure" not in st.session_state:
        st.session_state.connected_to_azure = False
    if "chat_backend" not in st.session_state:
        st.session_state.chat_backend = ChatBackend()
    if "user_question" not in st.session_state:
        st.session_state.user_question = ""
    
    st.header("Azure Data Chat Assistant ☁️")
    
    # Create a container for the main content with bottom margin
    main_content = st.container()
    with main_content:
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        with st.sidebar:
            st.subheader("Azure Connection")
            
            # Download from Azure section
            if st.button("Connect to Azure and Download Data"):
                with st.spinner("Connecting to Azure..."):
                    temp_dir, downloaded_files = download_from_azure()
                    
                    if downloaded_files:
                        st.session_state.connected_to_azure = True
                        st.session_state.temp_dir = temp_dir
                        st.session_state.downloaded_files = downloaded_files
                        
                        with st.spinner("Processing files..."):
                            success, message = st.session_state.chat_backend.process_files(downloaded_files)
                            st.session_state.data_processed = success
                            
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                    else:
                        st.error("Failed to download files from Azure")
            
            # Upload to Azure section
            st.subheader("Upload Files to Azure")
            
            uploaded_files = st.file_uploader(
                "Choose files to upload to Azure", 
                accept_multiple_files=True,
                type=["pdf", "csv", "xlsx", "xls", "txt", "md", "json", "xml", "html"]
            )
            
            if uploaded_files and st.button("Upload to Azure"):
                with st.spinner("Uploading files to Azure..."):
                    temp_upload_dir = tempfile.mkdtemp()
                    files_to_upload = {}
                    
                    # Save uploaded files to temporary directory
                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(temp_upload_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        mime_type = get_mimetype(file_path)
                        files_to_upload[file_path] = mime_type
                    
                    # Upload files to Azure
                    success = upload_to_azure(files_to_upload)
                    
                    if success:
                        st.success(f"✅ Successfully uploaded {len(files_to_upload)} files to Azure")
                        # Offer to process the newly uploaded files
                        if st.button("Process Uploaded Files"):
                            with st.spinner("Downloading and processing uploaded files..."):
                                temp_dir, downloaded_files = download_from_azure()
                                
                                if downloaded_files:
                                    st.session_state.connected_to_azure = True
                                    st.session_state.temp_dir = temp_dir
                                    st.session_state.downloaded_files = downloaded_files
                                    
                                    success, message = st.session_state.chat_backend.process_files(downloaded_files)
                                    st.session_state.data_processed = success
                                    
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                    else:
                        st.error("Failed to upload files to Azure. Check connection settings.")
             
            if st.session_state.connected_to_azure:
                st.success("✅ Connected to Azure")
                
                if st.session_state.data_processed:
                    st.success("✅ Data processed successfully")
                else:
                    st.warning("⚠️ Data connected but not processed successfully")
                
                if hasattr(st.session_state, 'downloaded_files') and st.session_state.downloaded_files:
                    st.subheader("Downloaded Files")
                    for file_path in st.session_state.downloaded_files:
                        st.write(f"- {os.path.basename(file_path)}")
            else:
                st.warning("Not connected to Azure")
             
            with st.expander("Environment Setup"):
                st.markdown("""
                ### Required Environment Variables
                
                You need to set these in your `.env` file:
                
                - `AZURE_CONN_STRING`: Your Azure connection string
                - `AZURE_CONTAINER_NAME`: Your Azure container name
                - `GROQ_API_KEY`: Your GROQ API key
                
                ### Supported File Types
                
                - PDF files (`.pdf`)
                - CSV files (`.csv`)
                - Excel files (`.xlsx`, `.xls`)
                - Text files (`.txt`, `.md`, `.json`, `.xml`, `.html`)
                """)
         
        st.subheader("Chat with your Azure data")
        
        # Chat history display area
        if "chat_history" in st.session_state and st.session_state.chat_history:
            for i, message in enumerate(st.session_state.chat_history):
                if i % 2 == 0:
                    st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
                else:
                    st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        
        if st.button("Clear Chat"):
            if st.session_state.chat_backend.clear_chat_history():
                st.success("Chat history cleared!")
                st.session_state.chat_history = None
            else:
                st.warning("No chat history to clear")
         
        with st.expander("About This Azure Data Assistant"):
            st.markdown("""
            This assistant helps you chat with your data stored in Azure Blob Storage.
            
            **Features:**
            - Downloads data from your Azure Blob Storage container
            - Uploads data to your Azure Blob Storage container
            - Processes various file types (PDF, CSV, Excel, text files)
            - Creates a searchable index of your data
            - Allows natural language queries about your data
            
            **How it works:**
            1. Connect to Azure and download your data or upload new files
            2. The system processes the files and creates a searchable index
            3. Ask questions about your data in natural language
            4. The system will search through your data and provide relevant answers
            
            **Example questions:**
            - "What kind of data is in my Azure storage?"
            - "Summarize the main findings in my PDF files"
            - "What are the average values in my dataset?"
            - "Find all entries related to [specific term]"
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Fixed bottom bar with search input and submit button
    st.markdown(
        """
        <div class="bottom-bar">
            <div id="bottom-search-container"></div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Add the search components to the fixed bottom bar
    bottom_container = st.container()
    with bottom_container:
        col1, col2 = st.columns([4, 1])
        with col1:
            user_question = st.text_input(
                "What would you like to know about your data?", 
                key="bottom_search",
                value=st.session_state.user_question,
                label_visibility="collapsed"
            )
        with col2:
            submit_button = st.button("Ask", use_container_width=True)
    
    # Handle user input when submit button is pressed
    if submit_button and user_question:
        st.session_state.user_question = user_question  # Save question to session state
        handle_user_input(user_question, st.session_state.chat_backend)
        # Clear input after submission
        st.session_state.user_question = ""

if __name__ == "__main__":
    main()