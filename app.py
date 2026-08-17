import io
import zipfile
from typing import List
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF

app = FastAPI(title="Ultimate PDF Studio API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "PDF Studio API with full PyMuPDF + pypdf features is live!"}

# 1. MERGE
@app.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Please upload at least 2 PDF files.")
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
            headers={"Content-Disposition": "attachment; filename=merged.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. SPLIT / EXTRACT PAGES
@app.post("/split")
async def split_pdf(
    file: UploadFile = File(...),
    start_page: int = Form(...),
    end_page: int = Form(...)
):
    try:
        file_bytes = await file.read()
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            raise HTTPException(status_code=400, detail=f"Invalid page range. Document has {total_pages} pages.")
        
        writer = PdfWriter()
        for i in range(start_page - 1, end_page):
            writer.add_page(reader.pages[i])
            
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=extracted_pages_{start_page}_to_{end_page}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. ROTATE
@app.post("/rotate")
async def rotate_pdf(file: UploadFile = File(...), angle: int = Form(...)):
    if angle not in [90, 180, 270]:
        raise HTTPException(status_code=400, detail="Angle must be 90, 180, or 270 degrees.")
    try:
        file_bytes = await file.read()
        reader = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(angle)
            writer.add_page(page)
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=rotated_{angle}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. ENCRYPT
@app.post("/encrypt")
async def encrypt_pdf(file: UploadFile = File(...), password: str = Form(...)):
    if not password:
        raise HTTPException(status_code=400, detail="Password cannot be empty.")
    try:
        file_bytes = await file.read()
        reader = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.encrypt(password)
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=protected.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. DECRYPT
@app.post("/decrypt")
async def decrypt_pdf(file: UploadFile = File(...), password: str = Form(...)):
    try:
        file_bytes = await file.read()
        reader = PdfReader(io.BytesIO(file_bytes))
        if not reader.is_encrypted:
            raise HTTPException(status_code=400, detail="This PDF is not encrypted.")
        
        success = reader.decrypt(password)
        if not success:
            raise HTTPException(status_code=401, detail="Incorrect password.")
            
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=unlocked.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 6. SEARCH & HIGHLIGHT
@app.post("/highlight")
async def highlight_pdf(file: UploadFile = File(...), search_text: str = Form(...)):
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
                "Content-Disposition": "attachment; filename=highlighted.pdf",
                "X-Total-Matches": str(total_matches)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 7. RENDER PAGE TO IMAGE (PNG)
@app.post("/render-page")
async def render_page(
    file: UploadFile = File(...),
    page_number: int = Form(1),
    zoom: float = Form(2.0)
):
    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if page_number < 1 or page_number > len(doc):
            raise HTTPException(status_code=400, detail=f"Invalid page number. Document has {len(doc)} pages.")
        
        page = doc[page_number - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        return Response(content=pix.tobytes("png"), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 8. ADVANCED TEXT EXTRACTION
@app.post("/extract-text")
async def extract_text(
    file: UploadFile = File(...),
    format_type: str = Form("text") # text, html, json, xml
):
    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        extracted_data = []
        
        for i, page in enumerate(doc):
            content = page.get_text(format_type)
            extracted_data.append({"page": i + 1, "content": content})
            
        return JSONResponse(content={"format": format_type, "pages": extracted_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 9. EXTRACT IMAGES (ZIP)
@app.post("/extract-images")
async def extract_images(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            img_count = 0
            for page_index in range(len(doc)):
                page = doc[page_index]
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    zip_file.writestr(f"page{page_index + 1}_img{img_index + 1}.{image_ext}", image_bytes)
                    img_count += 1
                    
        if img_count == 0:
            raise HTTPException(status_code=404, detail="No embedded images found in document.")
            
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=extracted_images.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 10. METADATA & TOC
@app.post("/metadata")
async def get_metadata(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return {
            "page_count": len(doc),
            "metadata": doc.metadata,
            "table_of_contents": doc.get_toc()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
