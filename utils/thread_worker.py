import inspect
import threading
import logging
import traceback
from typing import Callable, Any

logger = logging.getLogger(__name__)

class WorkerThread(threading.Thread):
    """
    Hilo de trabajo para ejecutar tareas pesadas sin bloquear la UI.
    Asegura que los callbacks se ejecuten siempre en el hilo principal (UI).
    """
    def __init__(
        self,
        app_root,
        target: Callable[..., Any],
        args: tuple = (),
        kwargs: dict = None,
        on_progress: Callable[[int, str], None] = None,
        on_success: Callable[[Any], None] = None,
        on_error: Callable[[str, str], None] = None,
        on_cancel: Callable[[], None] = None
    ):
        super().__init__()
        self.app_root = app_root
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.on_progress = on_progress
        self.on_success = on_success
        self.on_error = on_error
        self.on_cancel = on_cancel
        
        self.daemon = True  # El hilo muere si la aplicación se cierra
        self._is_cancelled = False

    def cancel(self):
        """Intenta cancelar la tarea (la tarea target debe chequear esto si soporta cancelación)"""
        self._is_cancelled = True

    def run(self):
        try:
            # Inyectar callback de progreso si la función lo acepta como parámetro
            try:
                sig = inspect.signature(self.target)
                if 'progress_callback' in sig.parameters:
                    self.kwargs['progress_callback'] = self._progress_wrapper
            except (ValueError, TypeError):
                # Si no se puede inspeccionar la firma, no inyectar
                pass
                
            result = self.target(*self.args, **self.kwargs)
            
            if self._is_cancelled:
                self._run_on_main_thread(self.on_cancel)
            else:
                self._run_on_main_thread(self.on_success, result)
                
        except MemoryError:
            msg = "El archivo es demasiado grande y la memoria se ha agotado."
            tb = traceback.format_exc()
            logger.error(f"{msg}\n{tb}")
            self._run_on_main_thread(self.on_error, msg, tb)
        except PermissionError:
            msg = "No se pudo acceder al archivo. Verifica que no esté abierto en otro programa."
            tb = traceback.format_exc()
            logger.error(f"{msg}\n{tb}")
            self._run_on_main_thread(self.on_error, msg, tb)
        except Exception as e:
            msg = f"Ocurrió un error inesperado: {str(e)}"
            tb = traceback.format_exc()
            logger.error(f"{msg}\n{tb}")
            self._run_on_main_thread(self.on_error, msg, tb)

    def _progress_wrapper(self, percent: int, message: str):
        """Envía el progreso al hilo principal."""
        if not self._is_cancelled:
            self._run_on_main_thread(self.on_progress, percent, message)

    def _run_on_main_thread(self, callback: Callable, *args):
        """Ejecuta un callback en el hilo principal usando app_root.after(0, ...)"""
        if callback:
            try:
                self.app_root.after(0, lambda: callback(*args))
            except Exception as e:
                # Ocurre si la ventana ya fue destruida
                logger.debug(f"No se pudo ejecutar callback en main thread: {e}")
