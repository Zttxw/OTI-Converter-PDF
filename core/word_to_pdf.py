import logging
import os
import subprocess
from pathlib import Path
from typing import Callable, Optional
import winreg

logger = logging.getLogger(__name__)

def detect_word_engine() -> str | None:
    """Detecta si Microsoft Word o LibreOffice están disponibles."""
    from utils.validators import check_office_installed
    
    # 1. Chequear Word via COM Dispatch (más seguro que registro)
    if check_office_installed("Word.Application"):
        return "word"
        
    # 2. Chequear LibreOffice
    libreoffice_paths = [
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "LibreOffice" / "program" / "soffice.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "LibreOffice" / "program" / "soffice.exe",
    ]
    
    for path in libreoffice_paths:
        if path.exists():
            return "libreoffice"
            
    # Chequear PATH
    try:
        if subprocess.run(["soffice", "--version"], capture_output=True).returncode == 0:
            return "libreoffice"
    except Exception:
        pass
        
    return None

def word_to_pdf(
    input_path: Path,
    output_path: Path,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Convierte Word a PDF usando docx2pdf (requiere MS Word) 
    o LibreOffice como fallback.
    """
    result = {
        "success": False,
        "output_path": None,
        "engine_used": None,
        "error": None
    }
    
    engine = detect_word_engine()
    if not engine:
        result["error"] = "No se detectó Microsoft Word ni LibreOffice instalados en el sistema."
        return result
        
    result["engine_used"] = engine
    
    # Nombre seguro
    final_output = output_path
    counter = 1
    while final_output.exists():
        final_output = output_path.parent / f"{output_path.stem}_{counter}{output_path.suffix}"
        counter += 1
        
    try:
        if engine == "word":
            if progress_callback:
                progress_callback(30, "Abriendo Microsoft Word en segundo plano...")
                
            from docx2pdf import convert
            # convert bloquea y no da callback granular
            convert(str(input_path), str(final_output))
            
        elif engine == "libreoffice":
            if progress_callback:
                progress_callback(30, "Ejecutando LibreOffice en segundo plano...")
                
            # LibreOffice headless
            cmd = [
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(final_output.parent),
                str(input_path)
            ]
            
            # Intentar encontrar ruta absoluta si 'soffice' no está en PATH
            if not subprocess.run(["where", "soffice"], capture_output=True).returncode == 0:
                libreoffice_path = Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "LibreOffice" / "program" / "soffice.exe"
                if libreoffice_path.exists():
                    cmd[0] = str(libreoffice_path)
                    
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                raise Exception(f"Error de LibreOffice: {process.stderr}")
                
            # LibreOffice nombra el archivo con el mismo nombre pero .pdf en outdir
            # Si se requería un nombre específico (counter), renombramos
            lo_output = final_output.parent / f"{input_path.stem}.pdf"
            if lo_output.exists() and lo_output != final_output:
                if final_output.exists():
                    final_output.unlink()
                lo_output.rename(final_output)

        if progress_callback:
            progress_callback(100, "¡Conversión finalizada!")

        result["success"] = True
        result["output_path"] = str(final_output)

    except PermissionError:
        result["error"] = "No se pudo escribir el archivo. Verifica que no esté abierto en otro programa."
    except Exception as e:
        logger.error(f"Error convirtiendo Word a PDF ({engine}): {e}")
        result["error"] = f"Error en la conversión: {e}"
        
    return result
