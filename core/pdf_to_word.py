import logging
from pathlib import Path
from typing import Callable, Optional
import sys

logger = logging.getLogger(__name__)

def pdf_to_word(
    input_path: Path,
    output_path: Path,
    start_page: int = 0,
    end_page: Optional[int] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Convierte un documento PDF a formato Word (docx).
    Usa lazy loading para pdf2docx para inicio rápido de la app.
    """
    result = {
        "success": False,
        "output_path": None,
        "warning": None,
        "error": None
    }
    
    try:
        from pdf2docx import Converter
        from pypdf import PdfReader
        
        # Verificar si está basado en imágenes (scanned PDF)
        # Esto es un chequeo muy simple: si no hay texto extraíble
        try:
            reader = PdfReader(str(input_path))
            first_page_text = reader.pages[0].extract_text()
            if not first_page_text or len(first_page_text.strip()) < 10:
                result["warning"] = "El PDF parece ser un documento escaneado. El Word generado podría contener solo imágenes."
        except Exception:
            pass # Ignorar errores en el chequeo

        # Nombre seguro
        final_output = output_path
        counter = 1
        while final_output.exists():
            final_output = output_path.parent / f"{output_path.stem}_{counter}{output_path.suffix}"
            counter += 1

        if progress_callback:
            progress_callback(10, "Iniciando motor de conversión...")

        cv = Converter(str(input_path))
        
        # Timeout y multiprocesamiento interno manejado por pdf2docx,
        # enviaremos mensajes de progreso artificiales si la librería no provee callbacks detallados.
        if progress_callback:
            progress_callback(50, "Convirtiendo estructura y texto (esto puede demorar)...")
            
        kwargs = {
            'start': start_page,
            'end': end_page
        }
        
        # Si end_page es None, convertir todo
        cv.convert(str(final_output), **kwargs)
        cv.close()
        
        if progress_callback:
            progress_callback(100, "Finalizando archivo Word...")

        result["success"] = True
        result["output_path"] = str(final_output)

    except Exception as e:
        logger.error(f"Error convirtiendo PDF a Word: {e}")
        result["error"] = str(e)
        
    return result
