import pytest
import os
from pathlib import Path
from pypdf import PdfWriter
from PIL import Image

@pytest.fixture
def sample_pdf_path(tmp_path):
    """Genera un PDF de prueba en memoria de 5 páginas."""
    path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    for _ in range(5):
        writer.add_blank_page(width=595, height=842) # A4 aprox
    with open(path, "wb") as f:
        writer.write(f)
    return path

@pytest.fixture
def sample_docx_path(tmp_path):
    """Crea un .docx mínimo."""
    path = tmp_path / "sample.docx"
    with open(path, "wb") as f:
        # Magic bytes PK para engañar validación básica
        f.write(b"PK\x03\x04" + b"\x00"*100) 
    return path

@pytest.fixture
def sample_jpg_path(tmp_path):
    """Genera imagen JPG."""
    path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (800, 600), color="white")
    img.save(path, "JPEG")
    return path

@pytest.fixture
def output_dir(tmp_path):
    return tmp_path

@pytest.fixture
def encrypted_pdf_path(tmp_path):
    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.encrypt("test123")
    with open(path, "wb") as f:
        writer.write(f)
    return path
