import logging
import os
import subprocess
from pathlib import Path
from typing import Callable, Optional
import winreg

logger = logging.getLogger(__name__)

def detect_powerpoint_engine() -> str | None:
    """Detecta si Microsoft PowerPoint o LibreOffice están disponibles."""
    # 1. Chequear PowerPoint
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\powerpnt.exe"
        )
        winreg.CloseKey(reg_key)
        return "powerpoint"
    except Exception:
        pass
        
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

def powerpoint_to_pdf(
    input_path: Path,
    output_path: Path,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Convierte PowerPoint a PDF usando COM Automation (requiere MS PowerPoint)
    o LibreOffice como fallback.
    """
    result = {
        "success": False,
        "output_path": None,
        "engine_used": None,
        "error": None
    }
    
    engine = detect_powerpoint_engine()
    if not engine:
        result["error"] = "No se detectó Microsoft PowerPoint ni LibreOffice instalados en el sistema."
        return result
        
    result["engine_used"] = engine
    
    # Nombre seguro
    final_output = output_path
    counter = 1
    while final_output.exists():
        final_output = output_path.parent / f"{output_path.stem}_{counter}{output_path.suffix}"
        counter += 1
        
    try:
        if engine == "powerpoint":
            if progress_callback:
                progress_callback(30, "Abriendo Microsoft PowerPoint en segundo plano...")
                
            import win32com.client
            import pythoncom
            
            # Inicializar COM para el hilo de fondo
            pythoncom.CoInitialize()
            powerpoint = None
            presentation = None
            try:
                powerpoint = win32com.client.Dispatch("PowerPoint.Application")
                
                if progress_callback:
                    progress_callback(50, "Cargando presentación de PowerPoint...")
                    
                presentation = powerpoint.Presentations.Open(str(input_path), WithWindow=False)
                
                if progress_callback:
                    progress_callback(75, "Exportando diapositivas a formato PDF...")
                    
                # 32 es ppSaveAsPDF
                presentation.SaveAs(str(final_output), 32)
                
                if progress_callback:
                    progress_callback(95, "Cerrando Microsoft PowerPoint...")
                    
                presentation.Close()
            finally:
                if powerpoint:
                    powerpoint.Quit()
                pythoncom.CoUninitialize()
            
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
        logger.error(f"Error convirtiendo PowerPoint a PDF ({engine}): {e}")
        result["error"] = f"Error en la conversión: {e}"
        
    return result
