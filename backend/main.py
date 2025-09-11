import os
import tempfile
import traceback
import chromadb
import streamlit as st
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from streamlit.runtime.uploaded_file_manager import UploadedFile
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

# Set page config FIRST
st.set_page_config(page_title="CV Align", layout="wide")

# Initialize all session state variables at the top level
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = None
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'progress' not in st.session_state:
    st.session_state.progress = 0

@st.cache_data(show_spinner=False)
def process_document(uploaded_file: UploadedFile) -> list[Document]:
    """Process uploaded PDF document and return text chunks."""
    temp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_file_path = temp_file.name

        # Load document
        loader = PyMuPDFLoader(temp_file_path)
        docs = loader.load()

        # Split text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""],
        )
        return text_splitter.split_documents(docs)

    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

@st.cache_resource(show_spinner=False)
def get_vector_collection():
    """Get or create ChromaDB collection."""
    ollama_ef = OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text:latest",
    )
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    return chroma_client.get_or_create_collection(
        name="cv_collection",
        embedding_function=ollama_ef,
        metadata={"hnsw:space": "cosine"},
    )

def process_resume(uploaded_file):
    """Handle the complete processing workflow."""
    try:
        st.session_state.processing = True
        st.session_state.progress = 0
        
        # Normalize filename
        normalized_name = uploaded_file.name.translate(
            str.maketrans({"-": "_", ".": "_", " ": "_", "(": "_", ")": "_"})
        )
        st.session_state.progress = 10
        
        # Process document
        all_splits = process_document(uploaded_file)
        st.session_state.progress = 40
        
        if not all_splits:
            raise Exception("No content extracted from document")
        
        # Add to vector store
        collection = get_vector_collection()
        documents, metadatas, ids = [], [], []
        
        for idx, split in enumerate(all_splits):
            documents.append(split.page_content)
            metadatas.append(split.metadata)
            ids.append(f"{normalized_name}_{idx}")
        
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        st.session_state.progress = 90
        
        # Store results in session state
        st.session_state.file_processed = {
            "name": uploaded_file.name,
            "normalized_name": normalized_name,
            "chunks": len(all_splits),
            "content": all_splits
        }
        st.session_state.progress = 100
        st.session_state.processed = True
        
    except Exception as e:
        st.error(f"Processing failed: {str(e)}")
        st.error(traceback.format_exc())
    finally:
        st.session_state.processing = False
        st.session_state.current_file = uploaded_file

def main():
    """Main Streamlit application."""
    # Sidebar
    with st.sidebar:
        st.header("CV Align")
        
        # Check dependencies
        deps_ok = check_dependencies()
        
        st.divider()
        
        uploaded_file = st.file_uploader(
            "**Upload Resume**",
            type=["pdf"],
            accept_multiple_files=False,
            help="Upload a PDF resume to process"
        )
        
        process_btn = st.button(
            "Process",
            disabled=not (uploaded_file and deps_ok and not st.session_state.processing),
            help="Process the uploaded resume" if deps_ok else "Fix dependency issues first"
        )

    # Main content
    st.title("CV Align - Resume Processing")

    # Dependency check
    if not deps_ok:
        st.error("⚠️ Please fix the dependency issues shown in the sidebar before proceeding.")
        return

    # Processing workflow
    if process_btn and uploaded_file and not st.session_state.processing:
        process_resume(uploaded_file)
        st.rerun()

    # Show progress if processing
    if st.session_state.processing:
        with st.container():
            st.progress(st.session_state.progress)
            st.info("Processing document... Please wait")
        return

    # Show results if processing complete
    if st.session_state.processed and st.session_state.file_processed:
        show_results()
        
        if st.button("Process another resume"):
            st.session_state.clear()
            st.rerun()
        
        # Keep the app alive
        st.stop()

    # Initial state
    if not uploaded_file:
        st.info("👈 Please upload a PDF resume using the sidebar")

def show_results():
    """Display processing results."""
    data = st.session_state.file_processed
    st.balloons()
    st.success("✅ Processing complete!")
    
    with st.expander("📊 Processing Details", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Original filename", data["name"])
            st.metric("Normalized name", data["normalized_name"])
        
        with col2:
            st.metric("Number of chunks", data["chunks"])
            st.metric("Total characters", sum(len(split.page_content) for split in data["content"]))
        
        if data["content"]:
            st.subheader("First chunk preview:")
            preview_text = data["content"][0].page_content[:500]
            if len(data["content"][0].page_content) > 500:
                preview_text += "..."
            st.text_area("Preview", preview_text, height=150, disabled=True)

def check_dependencies():
    """Check if all required services are available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            st.sidebar.error("❌ Ollama returned non-200 status")
            return False
    except Exception:
        st.sidebar.error("❌ Ollama not accessible")
        return False
    
    try:
        if not os.path.exists("./chroma_db"):
            os.makedirs("./chroma_db")
    except Exception:
        st.sidebar.error("❌ ChromaDB directory issue")
        return False
    
    st.sidebar.success("✅ All dependencies OK")
    return True

if __name__ == "__main__":
    main()