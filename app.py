from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF
import io
from typing import List

app = FastAPI(title="PDF Studio API")

# --- IMPORTANT: CORS CONFIGURATION ---
# This allows your Netlify frontend to talk to this Hugging Face backend.
# Once you have your Netlify URL, replace "*" with your exact Netlify URL (e.g., "https://my-app.netlify.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "PDF API is running! Send POST requests to /merge or /highlight."}

@app.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    """Merges multiple PDFs using pypdf."""
    writer = PdfWriter()
    
    for file in files:
        # Read the uploaded file into memory
        pdf_bytes = await file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer.append_pages_from_reader(reader)
        
    # Save merged PDF to a buffer
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=merged.pdf"}
    )

@app.post("/highlight")
async def highlight_pdf(file: UploadFile = File(...), search_text: str = Form(...)):
    """Highlights specific text in a PDF using PyMuPDF."""
    pdf_bytes = await file.read()
    
    # Open the PDF with PyMuPDF from memory
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Search and highlight
    for page in doc:
        text_instances = page.search_for(search_text)
        for inst in text_instances:
            page.add_highlight_annot(inst)
            
    # Save to buffer
    buffer = io.BytesIO(doc.tobytes())
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=highlighted.pdf"}
    )
