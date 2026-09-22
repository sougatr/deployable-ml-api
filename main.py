import fitz  # PyMuPDF
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from openai import AsyncOpenAI
import chromadb
from chromadb.utils import embedding_functions
import pydicom
from PIL import Image
import numpy as np
import base64
from io import BytesIO

# 1. Initialize FastAPI and OpenAI Client
app = FastAPI(title="Clinical AI Orchestrator with Multimodal Vision")
client = AsyncOpenAI(
    base_url="http://localhost:8080/v1",
    api_key="local-token-not-needed"
)

# 2. Vector DB Setup (RAG)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="clinical_guidelines", embedding_function=sentence_transformer_ef)

# 3. Data Structures
class ClinicalQuery(BaseModel):
    query: str

class IngestRequest(BaseModel):
    document_id: str
    text: str

# 4. Helper Functions
def process_image_to_base64(file_bytes: bytes, filename: str) -> str:
    """Parses standard images or DICOM files and converts to Base64 JPEG."""
    if filename.lower().endswith(".dcm"):
        dicom = pydicom.dcmread(BytesIO(file_bytes))
        pixels = dicom.pixel_array
        pixels = pixels - np.min(pixels)
        pixels = (pixels / np.max(pixels) * 255).astype(np.uint8)
        image = Image.fromarray(pixels)
    else:
        image = Image.open(BytesIO(file_bytes))
    
    if image.mode != "RGB":
        image = image.convert("RGB")
        
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_str}"

def chunk_medical_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list:
    """Splits document text into overlapping token windows to preserve clinical continuity."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

# 5. Core Endpoints
@app.post("/ingest")
async def ingest_text(request: IngestRequest):
    """Ingests small raw text snippets into ChromaDB."""
    try:
        collection.add(
            documents=[request.text],
            metadatas=[{"source": request.document_id}],
            ids=[request.document_id]
        )
        return {"status": "success", "message": f"Document {request.document_id} indexed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-pdf")
async def ingest_pdf(file: UploadFile = File(...)):
    """Ingests and chunks multi-page clinical PDF manuals into ChromaDB."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for this endpoint.")
    
    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
            
        doc.close()
        chunks = chunk_medical_text(full_text, chunk_size=400, overlap=50)
        
        if not chunks:
            raise ValueError("No extractable text found in this PDF (it may be a scanned image).")
            
        ids = [f"{file.filename}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": file.filename, "chunk_index": i} for i in range(len(chunks))]
        
        collection.add(documents=chunks, metadatas=metadatas, ids=ids)
        
        return {
            "status": "success", 
            "filename": file.filename, 
            "total_pages_parsed": total_pages,
            "vector_chunks_indexed": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.post("/analyze")
async def analyze_clinical_text(request: ClinicalQuery):
    """Performs RAG on the vector database and generates a clinical response."""
    try:
        results = collection.query(query_texts=[request.query], n_results=3)
        retrieved_context = "\n".join(results["documents"][0])
        
        system_prompt = f"Use ONLY the following context to answer the question:\n{retrieved_context}"
        
        response = await client.chat.completions.create(
            model="medgemma",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ],
            max_tokens=1024,
            temperature=0.1
        )
        return {"status": "success", "analysis": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference engine error: {str(e)}")

@app.post("/analyze-image")
async def analyze_image(query: str = Form(...), file: UploadFile = File(...)):
    """Parses medical images and routes them to the vision model."""
    try:
        file_bytes = await file.read()
        base64_image = process_image_to_base64(file_bytes, file.filename)
        
        response = await client.chat.completions.create(
            model="medgemma",
            messages=[
                {"role": "system", "content": "You are a clinical AI interpreting medical imaging."},
                {"role": "user", "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": base64_image}}
                ]}
            ],
            max_tokens=1024,
            temperature=0.1
        )
        return {"status": "success", "analysis": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision engine error: {str(e)}")