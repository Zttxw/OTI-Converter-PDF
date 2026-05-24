import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from utils.constants import LOG_DIR, LOG_FORMAT, LOG_RETENTION_DAYS

def setup_logger() -> logging.Logger:
    """
    Configura el logger central de la aplicación.
    Escribe logs en %APPDATA%/OTI-Converter/logs/oti_YYYY-MM-DD.log
    """
    logger = logging.getLogger()
    
    # Prevenir que se añadan múltiples handlers si se llama varias veces
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Fallback a stdout si no se puede crear directorio
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.error(f"No se pudo crear directorio de logs. Usando stdout: {e}")
        return logger

    # Configurar archivo log diario
    log_file = LOG_DIR / f"oti_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    try:
        # Rotación diaria, conservando 7 días
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.error(f"Error configurando FileHandler: {e}")

    # También loggear a consola si estamos en desarrollo o no empaquetados
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

    return logger

def clean_path_for_log(path: Path | str) -> str:
    """
    Retorna solo el nombre del archivo para no loggear rutas completas del usuario
    por motivos de privacidad.
    """
    if not path:
        return ""
    return Path(path).name
