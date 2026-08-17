import io
from typing import List
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF

app = FastAPI(title="PDF Studio API", version="1.0.0")

# CORS middleware allows your Netlify frontend (or local development) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with your exact Netlify domain later (e.g. "https://my-app.netlify.app")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "PDF Studio API is live on Render!"}


@app.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    """Merges two or more PDF files using pypdf."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Please upload at least 2 PDF files to merge.")

    try:
        writer = PdfWriter()
        for file in files:
            file_bytes = await file.read()
            reader = PdfReader(io.BytesIO(file_bytes))
            writer.append_pages_from_reader(reader)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=merged_document.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error merging PDFs: {str(e)}")


@app.post("/highlight")
async def highlight_pdf(
    file: UploadFile = File(...),
    search_text: str = Form(...)
):
    """Searches for target text and highlights all occurrences using PyMuPDF."""
    if not search_text.strip():
        raise HTTPException(status_code=400, detail="Search text cannot be empty.")

    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        total_matches = 0
        for page in doc:
            matches = page.search_for(search_text)
            for rect in matches:
                page.add_highlight_annot(rect)
                total_matches += 1

        output_buffer = io.BytesIO(doc.tobytes())
        output_buffer.seek(0)

        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=highlighted_document.pdf",
                "X-Total-Matches": str(total_matches)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error highlighting PDF: {str(e)}")
