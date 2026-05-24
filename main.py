import sys
import threading
import time

# Parche para cuando PyInstaller corre sin consola (sys.stdout es None)
class DummyWriter:
    def write(self, text): pass
    def flush(self): pass
    def isatty(self): return False

if sys.stdout is None:
    sys.stdout = DummyWriter()
if sys.stderr is None:
    sys.stderr = DummyWriter()

def check_python_version():
    if sys.version_info < (3, 11):
        import tkinter.messagebox
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        tkinter.messagebox.showerror(
            "Error de versión",
            "OTI - Converter requiere Python 3.11 o superior."
        )
        sys.exit(1)

def preload_heavy_modules():
    """Importa módulos pesados en un hilo daemon para acelerar primera conversión."""
    def _load():
        try:
            from pdf2docx import Converter
            import pdf2image
            import img2pdf
            import docx2pdf
        except Exception:
            pass # Ignoramos si falla, se manejará en el momento de uso
            
    t = threading.Thread(target=_load, daemon=True)
    t.start()

def main():
    check_python_version()
    
    # 1. Logger
    from utils.logger import setup_logger
    logger = setup_logger()
    logger.info("Iniciando OTI - Converter...")
    
    # 2. Configurar AppState
    from utils.app_state import AppState
    state = AppState.get()
    
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Inicializar app real directamente para evitar bugs de ventana
        from ui.app import OTIApp
        app = OTIApp()
        
        preload_heavy_modules()
        
        try:
            import pyi_splash
            pyi_splash.close()
        except ImportError:
            pass
            
        logger.info("UI lista. Entrando a mainloop.")
        app.mainloop()
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.critical(f"Fallo crítico al iniciar la aplicación:\n{tb}")
        
        # Intentar mostrar mensaje nativo
        import tkinter.messagebox
        import tkinter as tk
        error_root = tk.Tk()
        error_root.withdraw()
        
        try:
            from utils.constants import get_resource_path
            error_root.iconbitmap(get_resource_path('assets/logo.ico'))
        except Exception:
            pass
            
        try:
            with open("crash.txt", "w") as f:
                f.write(tb)
        except Exception:
            pass

        tkinter.messagebox.showerror(
            "Fallo Crítico",
            f"Ocurrió un error inesperado al iniciar OTI - Converter:\n\n{str(e)}\n\nRevisa los logs en %APPDATA%/OTI-Converter/logs/"
        )
        sys.exit(1)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
