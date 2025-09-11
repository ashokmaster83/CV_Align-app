from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from main_backup import process_uploaded_document, store_documents_in_vector_collection, retrieve_relevant_documents, generate_llm_response, rerank_documents_with_cross_encoder,normalize_filename

app = FastAPI()

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React frontend address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
'''
@app.post("/evaluate")
async def upload_cv(file: UploadFile = File(...), job_description: str = Form(...)):
    try:
        document_chunks = await process_uploaded_document(file)
        store_documents_in_vector_collection(document_chunks, normalize_filename(file.filename))

        search_results = retrieve_relevant_documents(job_description)
        retrieved_documents = search_results.get("documents", [[]])[0]

        if not retrieved_documents:
            return {"answer": "No relevant information found in the CV."}

        relevant_context, _ = rerank_documents_with_cross_encoder(job_description, retrieved_documents)

        response_text = ""
        for chunk in generate_llm_response(relevant_context, job_description):
            response_text += chunk

        return {"answer": response_text}
    
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}
'''
@app.post("/evaluate")
async def upload_cv(file: UploadFile = File(...), job_description: str = Form(...)):
    try:
        print("[DEBUG] Received file:", file.filename)
        document_chunks = await process_uploaded_document(file)
        print(f"[DEBUG] Processed {len(document_chunks)} chunks.")
        
        file_id = normalize_filename(file.filename)
        store_documents_in_vector_collection(document_chunks, file_id)
        print("[DEBUG] Stored chunks in ChromaDB.")

        search_results = retrieve_relevant_documents(job_description)
        retrieved_documents = search_results.get("documents", [[]])[0]
        print(f"[DEBUG] Retrieved {len(retrieved_documents)} docs for query.")

        if not retrieved_documents:
            return {"answer": "No relevant information found in the CV."}

        relevant_context, _ = rerank_documents_with_cross_encoder(job_description, retrieved_documents)
        print("[DEBUG] Re-ranked and selected context.")

        response_text = ""
        for chunk in generate_llm_response(relevant_context, job_description):
            print(f"[LLM Chunk] {chunk}")
            response_text += chunk

        print("[DEBUG] Final response ready.")
        return {"answer": response_text}
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {"answer": f"Error: {str(e)}"}
