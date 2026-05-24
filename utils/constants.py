import os
import sys
from pathlib import Path

# ══════════════════════════════════════════
# OTI - Converter — Constantes Globales
# ══════════════════════════════════════════

APP_NAME = "OTI - Converter"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Institución Pública"
APP_DESCRIPTION = "Gestor de PDFs offline para Windows"

# ══════════════════════════════════════════
# Rutas de la aplicación
# ══════════════════════════════════════════
def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta al recurso, compatible con PyInstaller (_MEIPASS)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

# Usar LOCALAPPDATA para evitar problemas de permisos o roaming
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", ""))) / "OTI-Converter"
APPDATA_DIR = USER_DATA_DIR # Alias para retrocompatibilidad
LOG_DIR = USER_DATA_DIR / "logs"
SETTINGS_PATH = USER_DATA_DIR / "settings.json"

# ══════════════════════════════════════════
# Límites
# ══════════════════════════════════════════
MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_FILENAME_LENGTH = 255

# ══════════════════════════════════════════
# Paleta de Colores Institucional
# ══════════════════════════════════════════
COLORS = {
    "primary":          "#3484A5",   # Azul institucional
    "secondary":        "#2CA792",   # Verde institucional
    "accent":           "#F0C84F",   # Amarillo institucional
    "bg_main":          "#1A1F2E",   # Fondo principal
    "bg_sidebar":       "#141824",   # Fondo sidebar
    "bg_card":          "#212636",   # Fondo tarjetas
    "bg_input":         "#2A3040",   # Fondo inputs
    "text_primary":     "#F0F2F5",   # Texto principal
    "text_secondary":   "#8A95A8",   # Texto secundario
    "border":           "#2E3650",   # Bordes
    "hover":            "#2E3A50",   # Hover general
    "success":          "#2CA792",   # Éxito
    "warning":          "#F0C84F",   # Advertencia
    "error":            "#E74C3C",   # Error
    "success_bg":       "#1A2E24",   # Fondo mensaje éxito
    "warning_bg":       "#2E2A1A",   # Fondo mensaje advertencia
    "error_bg":         "#2E1A1A",   # Fondo mensaje error
}

# ══════════════════════════════════════════
# Configuración de la UI
# ══════════════════════════════════════════
UI_WINDOW_WIDTH = 1100
UI_WINDOW_HEIGHT = 680
UI_SIDEBAR_WIDTH = 200
UI_FONT_FAMILY = "Segoe UI"

# ══════════════════════════════════════════
# Logging
# ══════════════════════════════════════════
LOG_RETENTION_DAYS = 7
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
