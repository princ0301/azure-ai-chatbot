import os
import pandas as pd
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_groq import ChatGroq
from langchain_openai import AzureChatOpenAI

import warnings
warnings.filterwarnings("ignore")

class ChatBackend:
    def __init__(self):
        load_dotenv()
        self.conversation = None
        self.vectorstore = None
        self.chat_history = None

    def process_file(self, file_path):
        """Extract text content from a file based on its extension"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf': 
                text = self.extract_text_from_pdf(file_path)
                return f"File: {os.path.basename(file_path)}\n\n" + text
                
            elif file_ext in ['.csv', '.xlsx', '.xls']: 
                if file_ext == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                 
                text = f"File: {os.path.basename(file_path)}\n"
                text += f"Columns: {', '.join(df.columns)}\n"
                text += f"Rows: {len(df)}\n\n"
                 
                text += "Sample data:\n"
                text += df.head(5).to_string() + "\n\n"
                 
                text += "Summary statistics:\n"
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    text += df[numeric_cols].describe().to_string()
                
                return text
            
            elif file_ext in ['.txt', '.md', '.json', '.xml', '.html']: 
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    return f"File: {os.path.basename(file_path)}\n\n" + file.read()
            
            else:
                return f"Unsupported file type: {file_ext} for file {os.path.basename(file_path)}"
        
        except Exception as e:
            return f"Error processing file {os.path.basename(file_path)}: {str(e)}"

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF file"""
        try:
            pdf_reader = PdfReader(pdf_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"Error extracting text from PDF {os.path.basename(pdf_path)}: {str(e)}"

    def process_files(self, file_paths):
        """Process multiple files and create a vector store from their content"""
        all_text = ""
        for file_path in file_paths:
            file_text = self.process_file(file_path)
            all_text += file_text + "\n\n" + "-" * 50 + "\n\n"
         
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        text_chunks = text_splitter.split_text(all_text)
        
        if not text_chunks:
            return False, "No text content was extracted from the files"
     
        self.vectorstore = self.create_vectorstore(text_chunks)
        
        if not self.vectorstore:
            return False, "Failed to create vector store"
         
        self.conversation = self.setup_conversation_chain(self.vectorstore)
        
        if not self.conversation:
            return False, "Failed to set up conversation chain"
        
        return True, f"Data processed successfully! Created {len(text_chunks)} chunks for searching."

    def create_vectorstore(self, text_chunks):
        """Create a vector store from text chunks using HuggingFace embeddings"""
        try:
            embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
            vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
            return vectorstore
        except Exception as e:
            print(f"Error creating vector store: {str(e)}")
            return None

    def setup_conversation_chain(self, vectorstore):
        """Set up the conversation chain with the LLM and vector store""" 
        groq_api_key = os.environ.get("GROQ_API_KEY")
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        os.environ["OPENAI_API_VERSION"] = "2023-05-15"
        
        try:
            if not azure_api_key or not azure_endpoint:
                print("Azure OpenAI API key or endpoint not found in environment variables")
                return None
             
            llm = ChatGroq(
                model="llama3-70b-8192",
                temperature=0.3,
            )

            # llm = AzureChatOpenAI(
            #     api_key=azure_api_key,
            #     azure_endpoint=azure_endpoint,
            #     deployment_name="gpt-4o-mini",
            #     temperature=0.2
            # )
            # print(llm.metadata)
             
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
                memory=memory,
                return_source_documents=True,
                verbose=False
            )
            
            return conversation_chain
        except Exception as e:
            print(f"Error setting up conversation chain: {str(e)}")
            return None

    def ask_question(self, question):
        """Process a user question and get a response from the conversation chain"""
        if self.conversation is None:
            return {"error": "Conversation chain not initialized. Process data first."}
        
        try:
            response = self.conversation.invoke({
                'question': question
            })
             
            self.chat_history = response['chat_history']
            
            return {
                "answer": response['answer'],
                "chat_history": response['chat_history'],
                "source_documents": response['source_documents'] if 'source_documents' in response else []
            }
        except Exception as e:
            return {"error": f"Error processing question: {str(e)}"}

    def clear_chat_history(self):
        """Clear the conversation history"""
        if self.conversation and hasattr(self.conversation, 'memory'):
            self.conversation.memory.clear()
            self.chat_history = None
            return True
        return False