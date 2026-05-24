import json
import logging
from pathlib import Path
from typing import Optional
from utils.constants import SETTINGS_PATH

logger = logging.getLogger(__name__)

class AppState:
    """
    Singleton que maneja el estado global de la aplicación.
    Principalmente la persistencia de la carpeta de destino
    y los archivos recientes.
    """
    _instance = None

    MAX_RECENT_FILES = 10

    def __init__(self):
        if AppState._instance is not None:
            raise Exception("Esta clase es un singleton. Usa AppState.get()")
        
        self.last_output_dir: Optional[Path] = None
        self.remember_output_dir: bool = True
        self.recent_files: list[Path] = []
        
        # Crear directorio si no existe
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"No se pudo crear el directorio de settings: {e}")

    @classmethod
    def get(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset(cls) -> None:
        """Resetea el singleton. Solo para uso en tests."""
        cls._instance = None

    def set_output_dir(self, path: Path) -> None:
        """Guarda la carpeta de destino en memoria y disco (si aplica)."""
        self.last_output_dir = path
        if self.remember_output_dir:
            self._save_to_disk()

    def get_output_dir(self, fallback: Path) -> Path:
        """
        Retorna la última carpeta válida guardada o el fallback.
        Maneja el caso donde la carpeta guardada fue eliminada.
        """
        if not self.remember_output_dir or not self.last_output_dir:
            return fallback

        if self.last_output_dir.exists() and self.last_output_dir.is_dir():
            return self.last_output_dir
        
        # Si la carpeta ya no existe, usar fallback
        logger.info(f"Carpeta guardada ya no existe: {self.last_output_dir}. Usando fallback.")
        return fallback

    def add_recent_file(self, path: Path | str) -> None:
        """
        Agrega un path a la lista de archivos recientes.
        Máximo MAX_RECENT_FILES (10) archivos, FIFO.
        Si el archivo ya existe en la lista, lo mueve al inicio.
        """
        p = Path(path).resolve()

        # Remover si ya existe (para re-posicionar al inicio)
        self.recent_files = [f for f in self.recent_files if f != p]

        # Insertar al inicio
        self.recent_files.insert(0, p)

        # Recortar al máximo
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]

        self._save_to_disk()

    def get_recent_files(self, limit: int = 10) -> list[Path]:
        """
        Retorna lista de los últimos archivos usados que aún existen.
        Filtra automáticamente los que hayan sido eliminados del disco.
        """
        limit = min(limit, self.MAX_RECENT_FILES)
        existing = [p for p in self.recent_files if p.exists()]

        # Si la lista cambió (se eliminaron archivos), persistir
        if len(existing) != len(self.recent_files):
            self.recent_files = existing
            self._save_to_disk()

        return existing[:limit]

    def _save_to_disk(self) -> None:
        """Persiste el estado en settings.json."""
        data = {
            "remember_output_dir": self.remember_output_dir,
            "recent_files": [str(p) for p in self.recent_files],
        }

        if self.last_output_dir:
            data["last_output_dir"] = str(self.last_output_dir.resolve())
        
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except PermissionError:
            logger.warning("Sin permisos de escritura para settings.json")
        except Exception as e:
            logger.error(f"Error al guardar settings.json: {e}")

    def _load_from_disk(self) -> None:
        """Carga el estado desde settings.json al iniciar la app."""
        if not SETTINGS_PATH.exists():
            return
            
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.remember_output_dir = data.get("remember_output_dir", True)
            
            saved_dir = data.get("last_output_dir")
            if saved_dir:
                path = Path(saved_dir)
                if path.exists() and path.is_dir():
                    self.last_output_dir = path

            # Cargar archivos recientes
            saved_recent = data.get("recent_files", [])
            self.recent_files = []
            for file_str in saved_recent:
                try:
                    p = Path(file_str)
                    if p.exists():
                        self.recent_files.append(p)
                except Exception:
                    pass  # Ignorar entradas corruptas

        except json.JSONDecodeError:
            logger.warning("settings.json corrupto. Usando defaults.")
        except Exception as e:
            logger.error(f"Error al leer settings.json: {e}")
