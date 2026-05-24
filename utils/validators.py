import os
import tempfile
import logging

logger = logging.getLogger(__name__)

def is_valid_pdf(file_path: str) -> bool:
    """Verifica si el archivo es realmente un PDF leyendo sus magic bytes."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            return header == b'%PDF'
    except Exception as e:
        logger.error(f"Error al validar PDF {file_path}: {e}")
        return False

def check_office_installed(app_name: str = "Word.Application") -> bool:
    """
    Verifica si Microsoft Office está instalado probando el COM Dispatch.
    app_name puede ser 'Word.Application' o 'Excel.Application'.
    """
    try:
        import win32com.client
        # Usamos DispatchEx para no interferir con instancias ya abiertas
        app = win32com.client.DispatchEx(app_name)
        app.Quit()
        return True
    except Exception as e:
        logger.warning(f"No se detectó {app_name}: {e}")
        return False

def get_safe_temp_dir() -> str:
    """Crea y retorna un directorio temporal seguro para operaciones."""
    return tempfile.mkdtemp(prefix="oti_conv_")
