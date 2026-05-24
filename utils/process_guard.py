import os
import json
import ctypes
import logging
from datetime import datetime
from pathlib import Path
from utils.constants import USER_DATA_DIR, APP_VERSION

logger = logging.getLogger(__name__)

_GLOBAL_MUTEX = None
LOCK_FILE_PATH = USER_DATA_DIR / "app.lock"

def acquire_mutex(mutex_name: str = "Global\\OTI_Converter_Running") -> bool:
    """
    Capa 1: Intenta crear un Mutex global.
    Retorna True si tuvo éxito (primera instancia).
    Retorna False si ya existe (la app ya está corriendo).
    """
    global _GLOBAL_MUTEX
    
    # Prevenir recolección de basura
    _GLOBAL_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
    
    # 183 = ERROR_ALREADY_EXISTS
    if ctypes.windll.kernel32.GetLastError() == 183:
        # Ya está corriendo
        return False
        
    return True

def write_lock_file():
    """
    Capa 2: Escribe un archivo .lock con metadatos del proceso actual.
    """
    try:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        lock_data = {
            "pid": os.getpid(),
            "started_at": datetime.now().isoformat(),
            "version": APP_VERSION,
            "hostname": os.environ.get("COMPUTERNAME", "Unknown")
        }
        
        with open(LOCK_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, indent=4)
            
    except Exception as e:
        logger.warning(f"No se pudo escribir el archivo lock: {e}")

def remove_lock_file():
    """
    Elimina el archivo .lock al cerrar la app limpiamente.
    """
    try:
        if LOCK_FILE_PATH.exists():
            os.remove(LOCK_FILE_PATH)
    except Exception as e:
        logger.warning(f"No se pudo eliminar el archivo lock: {e}")

def validate_lock_file() -> bool:
    """
    Verifica si el lock file existe y si su PID pertenece a un proceso vivo.
    """
    try:
        import psutil
        
        if not LOCK_FILE_PATH.exists():
            return False
            
        with open(LOCK_FILE_PATH, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
            
        pid = lock_data.get("pid")
        if pid and psutil.pid_exists(pid):
            # Verificar si el nombre del proceso coincide para evitar falsos positivos
            try:
                proc = psutil.Process(pid)
                if "oti_converter" in proc.name().lower() or "python" in proc.name().lower():
                    return True
            except psutil.NoSuchProcess:
                pass
                
        # Si llegamos aquí, el proceso murió (crash) o no es OTI, limpiamos el fantasma
        remove_lock_file()
        return False
        
    except Exception as e:
        logger.warning(f"Error validando lock file: {e}")
        # En caso de error, preferimos permitir la ejecución pero avisar
        return False

def is_app_running(exe_name: str = "OTI_Converter.exe") -> bool:
    """
    Capa 3: Busca en los procesos activos de Windows ignorando el proceso actual.
    """
    try:
        import psutil
        current_pid = os.getpid()
        exe_lower = exe_name.lower()
        
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['pid'] != current_pid and proc.info['name']:
                    if proc.info['name'].lower() == exe_lower:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        return False
    except ImportError:
        logger.error("psutil no está instalado. No se puede verificar is_app_running.")
        return False

def check_single_instance() -> bool:
    """
    Wrapper que ejecuta la Capa 1 y Capa 2 para el inicio de la app.
    Retorna True si es seguro iniciar. False si ya hay otra instancia.
    """
    # 1. Chequeo Mutex
    if not acquire_mutex():
        return False
        
    # 2. Chequeo Lock File
    if validate_lock_file():
        return False
        
    # Es la primera instancia, registramos
    write_lock_file()
    return True

def bring_window_to_front(window_title: str):
    """
    Busca una ventana por su título y la trae al frente.
    """
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, window_title)
        if hwnd:
            # 9 = SW_RESTORE
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception as e:
        logger.warning(f"No se pudo traer la ventana al frente: {e}")
