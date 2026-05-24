import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

def merge_pdfs(
    input_paths: list[Path],
    output_path: Path,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Une múltiples archivos PDF en uno solo.
    Preserva bookmarks. Tolerante a fallos parciales.
    """
    from pypdf import PdfWriter, PdfReader
    
    result = {
        "success": False,
        "output": str(output_path),
        "pages_total": 0,
        "files_processed": 0,
        "files_failed": 0,
        "error": None
    }
    
    if not input_paths:
        result["error"] = "No se proporcionaron archivos de entrada."
        return result

    merger = PdfWriter()
    total_files = len(input_paths)
    
    try:
        for idx, path in enumerate(input_paths):
            if progress_callback:
                percent = int((idx / total_files) * 90)
                progress_callback(percent, f"Uniendo archivo {idx+1} de {total_files}...")
                
            try:
                # Validar existencia
                if not path.exists():
                    logger.warning(f"Archivo no existe y será omitido: {path}")
                    result["files_failed"] += 1
                    continue
                    
                merger.append(str(path))
                result["files_processed"] += 1
            except Exception as e:
                logger.error(f"Error al procesar {path}: {e}")
                result["files_failed"] += 1
                
        if result["files_processed"] == 0:
            result["error"] = "No se pudo procesar ningún archivo válido."
            return result
            
        if progress_callback:
            progress_callback(95, "Guardando archivo final...")
            
        # Manejo de nombres si ya existe
        final_output = output_path
        counter = 1
        while final_output.exists():
            final_output = output_path.parent / f"{output_path.stem}_{counter}{output_path.suffix}"
            counter += 1
            
        result["output"] = str(final_output)
        
        with open(final_output, "wb") as out_file:
            merger.write(out_file)
            
        result["pages_total"] = len(merger.pages)
        result["success"] = True
        
    except Exception as e:
        logger.error(f"Error crítico uniendo PDFs: {e}")
        result["error"] = str(e)
    finally:
        merger.close()
        
    return result
