import io

from docx import Document
from fastapi import HTTPException
from pypdf import PdfReader

# Para que un documento enorme no llene el contexto
MAX_CHARS_PER_FILE = 20000


def extract_pdf(data):
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    # algunos pdf rellenan cada linea con espacios
    lines = []
    for line in "\n".join(pages).splitlines():
        lines.append(line.rstrip())
    return "\n".join(lines)


def extract_docx(data):
    document = Document(io.BytesIO(data))
    paragraphs = []
    for paragraph in document.paragraphs:
        paragraphs.append(paragraph.text)
    return "\n".join(paragraphs)


# Saca el texto de un adjunto segun la extension (solo pdf y docx)
def extract_text(filename, data):
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            text = extract_pdf(data)
        elif name.endswith(".docx"):
            text = extract_docx(data)
        else:
            raise HTTPException(status_code=415, detail=f"{filename}: solo se aceptan archivos .pdf y .docx")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail=f"{filename}: no se pudo leer el archivo")

    text = text.strip()
    # un pdf escaneado (solo imagenes) no tiene texto
    if text == "":
        return "(no se pudo extraer texto de este archivo)"
    return text[:MAX_CHARS_PER_FILE]


# Junta la transcripcion con el texto de cada adjunto, separados para que el modelo sepa de donde viene cada parte
def build_transcript(transcript, files):
    parts = [transcript.strip()]
    for filename, data in files:
        parts.append(f"--- attachment: {filename} ---\n{extract_text(filename, data)}")
    return "\n\n".join(parts)
