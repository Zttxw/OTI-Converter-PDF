import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

def pdf_to_images(
    input_path: Path,
    output_dir: Path,
    format: str = "jpg",
    dpi: int = 150,
    page_range: Optional[tuple[int, int]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Convierte un PDF a imágenes usando PyMuPDF (fitz).
    Esto es 100% nativo y no requiere binarios externos de poppler.
    """
    result = {"success": False, "images_created": 0, "error": None}
    
    try:
        import fitz  # PyMuPDF
        
        fmt = format.lower()
        if fmt not in ["jpg", "png", "jpeg"]:
            fmt = "jpg"
            
        if progress_callback:
            progress_callback(10, "Abriendo documento PDF...")
            
        doc = fitz.open(str(input_path))
        
        start_page = 0
        end_page = len(doc) - 1
        
        if page_range:
            # page_range es 1-indexed, PyMuPDF es 0-indexed
            start_page = max(0, page_range[0] - 1)
            end_page = min(len(doc) - 1, page_range[1] - 1)
            
        total_pages = (end_page - start_page) + 1
        
        if total_pages <= 0:
            result["error"] = "Rango de páginas inválido."
            return result
            
        base_name = input_path.stem
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        
        for i, page_num in enumerate(range(start_page, end_page + 1)):
            if progress_callback:
                percent = int(10 + (i / total_pages) * 90)
                progress_callback(percent, f"Guardando imagen {i+1} de {total_pages}...")
                
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix, alpha=False if fmt in ["jpg", "jpeg"] else True)
            
            out_name = output_dir / f"{base_name}_pagina_{page_num+1:03d}.{fmt}"
            
            counter = 1
            final_out = out_name
            while final_out.exists():
                final_out = output_dir / f"{base_name}_pagina_{page_num+1:03d}_{counter}.{fmt}"
                counter += 1
                
            if fmt in ["jpg", "jpeg"]:
                pix.save(str(final_out))
            else:
                pix.save(str(final_out), "png")
                
            result["images_created"] += 1
            
        doc.close()
        result["success"] = True
        
    except Exception as e:
        logger.error(f"Error convirtiendo PDF a imágenes (fitz): {e}")
        result["error"] = str(e)
        
    return result

