import pytest
from pathlib import Path
import json
from utils.app_state import AppState

def test_singleton():
    AppState._instance = None # Reset for test
    a = AppState.get()
    b = AppState.get()
    assert a is b

def test_persiste_entre_paneles(tmp_path):
    AppState._instance = None
    state = AppState.get()
    
    test_dir = tmp_path / "some_dir"
    test_dir.mkdir()
    
    state.set_output_dir(test_dir)
    assert state.get_output_dir(fallback=Path("C:/")) == test_dir

def test_carpeta_eliminada(tmp_path):
    AppState._instance = None
    state = AppState.get()
    
    test_dir = tmp_path / "to_be_deleted"
    test_dir.mkdir()
    
    state.set_output_dir(test_dir)
    test_dir.rmdir() # Eliminada
    
    fallback = Path("C:/fallback")
    assert state.get_output_dir(fallback=fallback) == fallback

def test_primera_vez_sin_settings(tmp_path, monkeypatch):
    AppState._instance = None
    
    # Mock settings path
    settings_file = tmp_path / "settings.json"
    import utils.constants
    monkeypatch.setattr(utils.constants, "SETTINGS_PATH", settings_file)
    
    state = AppState.get()
    state._load_from_disk()
    
    fallback = Path("C:/documents")
    assert state.get_output_dir(fallback=fallback) == fallback
