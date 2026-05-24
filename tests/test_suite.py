"""
OTI-Converter — Suite de Tests Completa.

Ejecutar con:  pytest tests/test_suite.py -v
"""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pypdf import PdfReader, PdfWriter
from PIL import Image


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def pdf_5pages(tmp_path):
    """Genera un PDF sintético de 5 páginas en blanco."""
    path = tmp_path / "test_5pages.pdf"
    writer = PdfWriter()
    for _ in range(5):
        writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def pdf_3pages(tmp_path):
    """Genera un PDF sintético de 3 páginas en blanco."""
    path = tmp_path / "test_3pages.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def pdf_2pages(tmp_path):
    """Genera un PDF sintético de 2 páginas en blanco."""
    path = tmp_path / "test_2pages.pdf"
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def three_png_images(tmp_path):
    """Genera 3 imágenes PNG sintéticas de colores distintos."""
    paths = []
    colors = ["red", "green", "blue"]
    for i, color in enumerate(colors):
        p = tmp_path / f"image_{i+1:02d}.png"
        img = Image.new("RGB", (200, 300), color=color)
        img.save(p, "PNG")
        paths.append(p)
    return paths


@pytest.fixture
def fake_pdf_file(tmp_path):
    """Genera un archivo .pdf que empieza con magic bytes %PDF."""
    path = tmp_path / "real_magic.pdf"
    path.write_bytes(b"%PDF-1.4 fake content for testing")
    return path


@pytest.fixture
def fake_text_as_pdf(tmp_path):
    """Genera un archivo .pdf con contenido de texto plano (magic bytes incorrectos)."""
    path = tmp_path / "fake.pdf"
    path.write_text("This is not a real PDF file", encoding="utf-8")
    return path


@pytest.fixture
def app_state_dir(tmp_path, monkeypatch):
    """Configura AppState para usar un directorio temporal en tests."""
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("utils.constants.SETTINGS_PATH", settings_path)
    # Resetear singleton
    from utils.app_state import AppState
    AppState._reset()
    yield tmp_path
    AppState._reset()


class MockAppRoot:
    """
    Mock de app_root para tests de WorkerThread.
    Ejecuta callbacks directamente en lugar de programarlos con Tk.after().
    """
    def after(self, delay, callback):
        callback()


# ═══════════════════════════════════════════════════════════════
# TESTS DE CORE — Integración ligera
# ═══════════════════════════════════════════════════════════════

class TestPdfMerge:
    """Tests para core/pdf_merge.py"""

    def test_pdf_merge(self, pdf_3pages, pdf_2pages, tmp_path):
        """Merge de 2 PDFs sintéticos resulta en la suma de páginas."""
        from core.pdf_merge import merge_pdfs

        output = tmp_path / "merged.pdf"
        result = merge_pdfs(
            input_paths=[pdf_3pages, pdf_2pages],
            output_path=output,
        )

        assert result["success"] is True
        assert result["files_processed"] == 2
        assert result["files_failed"] == 0

        # Verificar que el PDF tiene 3 + 2 = 5 páginas
        reader = PdfReader(str(result["output"]))
        assert len(reader.pages) == 5

    def test_pdf_merge_no_files(self, tmp_path):
        """Merge sin archivos retorna error."""
        from core.pdf_merge import merge_pdfs

        result = merge_pdfs(input_paths=[], output_path=tmp_path / "out.pdf")
        assert result["success"] is False
        assert result["error"] is not None


class TestPdfSplit:
    """Tests para core/pdf_split.py"""

    def test_pdf_split_by_pages(self, pdf_5pages, tmp_path):
        """Divide un PDF de 5 páginas en 5 archivos de 1 página cada uno."""
        from core.pdf_split import split_by_pages

        result = split_by_pages(
            input_path=pdf_5pages,
            output_dir=tmp_path,
            pages_per_file=1,
        )

        assert result["success"] is True
        assert result["files_created"] == 5

        # Verificar que cada archivo tiene 1 página
        pdf_files = sorted(tmp_path.glob("*_parte_*.pdf"))
        assert len(pdf_files) == 5
        for f in pdf_files:
            reader = PdfReader(str(f))
            assert len(reader.pages) == 1

    def test_pdf_split_by_ranges(self, pdf_5pages, tmp_path):
        """Divide por rangos '1-2, 4', genera 2 archivos (2 pág + 1 pág)."""
        from core.pdf_split import split_by_ranges

        ranges = [(1, 2), (4, 4)]
        result = split_by_ranges(
            input_path=pdf_5pages,
            output_dir=tmp_path,
            ranges=ranges,
        )

        assert result["success"] is True
        assert result["files_created"] == 2

        # Buscar archivos de rango generados
        rango_files = sorted(tmp_path.glob("*_rango_*.pdf"))
        assert len(rango_files) == 2

        # El primer rango (1-2) debería tener 2 páginas
        r1 = PdfReader(str(rango_files[0]))
        assert len(r1.pages) == 2

        # El segundo rango (4-4) debería tener 1 página
        r2 = PdfReader(str(rango_files[1]))
        assert len(r2.pages) == 1

    def test_get_pdf_page_count_and_thumbnails(self, pdf_3pages):
        """Verifica que se pueda obtener correctamente el conteo de páginas y los thumbnails PIL."""
        from core.pdf_split import get_pdf_page_count_and_thumbnails
        from PIL import Image

        result = get_pdf_page_count_and_thumbnails(str(pdf_3pages), max_thumbnails=2)

        assert result["success"] is True
        assert result["total_pages"] == 3
        assert len(result["thumbnails"]) == 2
        for img in result["thumbnails"]:
            assert isinstance(img, Image.Image)


class TestPdfMetadata:
    """Tests para core/pdf_metadata.py"""

    def test_pdf_metadata_read_write(self, pdf_5pages, tmp_path):
        """Escribe metadatos, los lee de vuelta y verifica que coinciden."""
        from core.pdf_metadata import set_metadata, get_metadata

        output = tmp_path / "with_meta.pdf"
        meta_to_set = {
            "title": "Documento de Prueba",
            "author": "OTI Test",
            "subject": "Testing",
        }

        # Escribir
        write_result = set_metadata(
            input_path=pdf_5pages,
            output_path=output,
            metadata=meta_to_set,
        )
        assert write_result["success"] is True
        assert write_result["output_path"].exists()

        # Leer
        read_result = get_metadata(input_path=write_result["output_path"])
        assert read_result["success"] is True

        read_meta = read_result["metadata"]
        assert read_meta["title"] == "Documento de Prueba"
        assert read_meta["author"] == "OTI Test"
        assert read_meta["subject"] == "Testing"
        assert read_meta["pages"] == 5

    def test_pdf_metadata_date_parser(self):
        """Parser de fechas maneja formatos completos, incompletos y malformados sin excepción."""
        from core.pdf_metadata import _parse_pdf_date

        # Fecha completa
        assert _parse_pdf_date("D:20231215103045+05'00'") == "2023-12-15 10:30:45"

        # Fecha sin zona horaria
        assert _parse_pdf_date("D:20231215103045") == "2023-12-15 10:30:45"

        # Solo fecha (sin hora)
        assert _parse_pdf_date("D:20231215") == "2023-12-15 00:00:00"

        # Solo año y mes
        assert _parse_pdf_date("D:202312") == "2023-12-01 00:00:00"

        # Solo año
        assert _parse_pdf_date("D:2023") == "2023-01-01 00:00:00"

        # Malformado — no debe lanzar excepción, retorna algo
        result = _parse_pdf_date("BASURA_TOTAL")
        assert result is not None  # No lanzó excepción

        # Vacío
        assert _parse_pdf_date("") is None
        assert _parse_pdf_date(None) is None

        # Con zona negativa
        assert _parse_pdf_date("D:20230101120000-03'00'") == "2023-01-01 12:00:00"


class TestImageToPdf:
    """Tests para core/image_to_pdf.py"""

    def test_image_to_pdf(self, three_png_images, tmp_path):
        """Convierte 3 imágenes PNG a un PDF de 3 páginas."""
        from core.image_to_pdf import images_to_pdf

        output = tmp_path / "images_combined.pdf"
        result = images_to_pdf(
            input_paths=three_png_images,
            output_path=output,
        )

        assert result["success"] is True
        assert result["pages"] == 3

        # Verificar que el PDF tiene 3 páginas
        reader = PdfReader(result["output_path"])
        assert len(reader.pages) == 3


# ═══════════════════════════════════════════════════════════════
# TESTS DE UTILS — Unitarios
# ═══════════════════════════════════════════════════════════════

class TestFileValidator:
    """Tests para utils/file_validator.py"""

    def test_file_validator_magic_bytes_pdf(self, fake_pdf_file):
        """Un archivo que empieza con %PDF pasa la validación de magic bytes."""
        from utils.file_validator import FileValidator

        valid, msg = FileValidator.validate_magic_bytes(fake_pdf_file, 'pdf')
        assert valid is True
        assert msg == ""

    def test_file_validator_magic_bytes_pdf_fail(self, fake_text_as_pdf):
        """Un archivo .pdf con contenido de texto falla la validación de magic bytes."""
        from utils.file_validator import FileValidator

        valid, msg = FileValidator.validate_magic_bytes(fake_text_as_pdf, 'pdf')
        assert valid is False
        assert "PDF" in msg

    def test_file_validator_size_limit(self, tmp_path):
        """Un archivo que supera el límite de tamaño (mockeado) falla con el error correcto."""
        from utils.file_validator import FileValidator

        big_file = tmp_path / "big.pdf"
        big_file.write_bytes(b"%PDF" + b"\x00" * 100)

        # Mockear st_size para simular 600 MB
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = MagicMock(st_size=600 * 1024 * 1024)
            valid, msg = FileValidator.validate_size(big_file, max_mb=500)

        assert valid is False
        assert "500" in msg

    def test_file_validator_invalid_chars(self):
        """Caracteres inválidos en Windows son sanitizados correctamente."""
        from utils.file_validator import FileValidator

        dirty_name = 'archivo<test>:con"caracteres|inválidos?*.pdf'
        clean_name = FileValidator.sanitize_filename(dirty_name)

        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            assert char not in clean_name

        # Debe mantener caracteres válidos
        assert "archivo" in clean_name
        assert ".pdf" in clean_name

    def test_file_validator_batch(self, tmp_path):
        """Valida una lista mixta de archivos válidos e inválidos."""
        from utils.file_validator import FileValidator

        # Crear archivo válido
        valid_pdf = tmp_path / "good.pdf"
        valid_pdf.write_bytes(b"%PDF-1.4 valid content")

        # Crear archivo inválido (no existe)
        missing_file = tmp_path / "no_existe.pdf"

        # Crear archivo con magic bytes incorrectos
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"NOT A PDF AT ALL")

        valid_paths, errors = FileValidator.validate_batch(
            [valid_pdf, missing_file, bad_pdf],
            allowed_types=['pdf']
        )

        assert len(valid_paths) == 1
        assert valid_paths[0] == valid_pdf
        assert str(missing_file) in errors
        assert str(bad_pdf) in errors


class TestAppState:
    """Tests para utils/app_state.py"""

    def test_app_state_recent_files(self, app_state_dir):
        """Agrega 12 archivos recientes, verifica que solo se guardan los últimos 10."""
        from utils.app_state import AppState

        state = AppState.get()

        # Crear 12 archivos reales
        files = []
        for i in range(12):
            f = app_state_dir / f"file_{i:02d}.pdf"
            f.write_bytes(b"%PDF test")
            files.append(f)

        # Agregar los 12
        for f in files:
            state.add_recent_file(f)

        recent = state.get_recent_files(limit=10)
        assert len(recent) == 10

        # El más reciente debe ser el último agregado
        assert recent[0] == files[11].resolve()

        # Los 2 primeros archivos no deben estar
        resolved_recent = [p.resolve() for p in recent]
        assert files[0].resolve() not in resolved_recent
        assert files[1].resolve() not in resolved_recent

    def test_app_state_persistence(self, app_state_dir):
        """Guarda estado, resetea el singleton y verifica que los datos persisten."""
        from utils.app_state import AppState

        # Configurar estado
        state = AppState.get()
        test_dir = app_state_dir / "output_test"
        test_dir.mkdir()
        state.set_output_dir(test_dir)

        test_file = app_state_dir / "recent_test.pdf"
        test_file.write_bytes(b"%PDF test")
        state.add_recent_file(test_file)

        # Resetear singleton y crear nueva instancia
        AppState._reset()
        new_state = AppState.get()
        new_state._load_from_disk()

        # Verificar persistencia
        assert new_state.last_output_dir == test_dir
        assert len(new_state.recent_files) == 1
        assert new_state.recent_files[0] == test_file.resolve()


# ═══════════════════════════════════════════════════════════════
# TESTS DE THREAD_WORKER — Concurrencia
# ═══════════════════════════════════════════════════════════════

class TestWorkerThread:
    """Tests para utils/thread_worker.py"""

    def test_worker_success(self):
        """Tarea exitosa invoca on_success con el resultado correcto."""
        from utils.thread_worker import WorkerThread

        result_event = threading.Event()
        results = {}

        def simple_task():
            return {"value": 42}

        def on_success(result):
            results["data"] = result
            result_event.set()

        worker = WorkerThread(
            app_root=MockAppRoot(),
            target=simple_task,
            on_success=on_success,
        )
        worker.start()
        assert result_event.wait(timeout=5), "on_success no fue invocado a tiempo"
        assert results["data"]["value"] == 42

    def test_worker_error(self):
        """Tarea con excepción invoca on_error con el mensaje correcto."""
        from utils.thread_worker import WorkerThread

        error_event = threading.Event()
        errors = {}

        def failing_task():
            raise ValueError("algo salió mal")

        def on_error(msg, tb):
            errors["msg"] = msg
            errors["tb"] = tb
            error_event.set()

        worker = WorkerThread(
            app_root=MockAppRoot(),
            target=failing_task,
            on_error=on_error,
        )
        worker.start()
        assert error_event.wait(timeout=5), "on_error no fue invocado a tiempo"
        assert "algo salió mal" in errors["msg"]

    def test_worker_progress(self):
        """Tarea que emite 5 actualizaciones de progreso, todas son recibidas."""
        from utils.thread_worker import WorkerThread

        done_event = threading.Event()
        progress_updates = []

        def task_with_progress(progress_callback=None):
            for i in range(5):
                if progress_callback:
                    progress_callback(i * 20, f"Paso {i+1}")
            return "done"

        def on_progress(percent, msg):
            progress_updates.append((percent, msg))

        def on_success(result):
            done_event.set()

        worker = WorkerThread(
            app_root=MockAppRoot(),
            target=task_with_progress,
            on_progress=on_progress,
            on_success=on_success,
        )
        worker.start()
        assert done_event.wait(timeout=5), "Tarea no completó a tiempo"
        assert len(progress_updates) == 5
        assert progress_updates[0] == (0, "Paso 1")
        assert progress_updates[4] == (80, "Paso 5")

    def test_worker_memory_error(self):
        """MemoryError se maneja con mensaje amigable."""
        from utils.thread_worker import WorkerThread

        error_event = threading.Event()
        errors = {}

        def oom_task():
            raise MemoryError("sin memoria")

        def on_error(msg, tb):
            errors["msg"] = msg
            error_event.set()

        worker = WorkerThread(
            app_root=MockAppRoot(),
            target=oom_task,
            on_error=on_error,
        )
        worker.start()
        assert error_event.wait(timeout=5), "on_error no fue invocado a tiempo"
        assert "memoria" in errors["msg"].lower()

    def test_worker_permission_error(self):
        """PermissionError se maneja con mensaje amigable."""
        from utils.thread_worker import WorkerThread

        error_event = threading.Event()
        errors = {}

        def perm_task():
            raise PermissionError("acceso denegado")

        def on_error(msg, tb):
            errors["msg"] = msg
            error_event.set()

        worker = WorkerThread(
            app_root=MockAppRoot(),
            target=perm_task,
            on_error=on_error,
        )
        worker.start()
        assert error_event.wait(timeout=5), "on_error no fue invocado a tiempo"
        assert "archivo" in errors["msg"].lower() or "acceder" in errors["msg"].lower()


class TestPdfCompress:
    """Tests para core/pdf_compress.py"""

    @pytest.fixture
    def pdf_with_image(self, tmp_path):
        """Genera un PDF con una imagen pesada embebida para pruebas de compresión."""
        pdf_path = tmp_path / "pdf_with_image.pdf"
        img = Image.new("RGB", (1000, 1200), color="blue")
        img.save(pdf_path, "PDF", resolution=300.0)
        return pdf_path

    @pytest.fixture
    def encrypted_pdf(self, pdf_3pages, tmp_path):
        """Genera un PDF cifrado con contraseña."""
        enc_path = tmp_path / "encrypted.pdf"
        reader = PdfReader(str(pdf_3pages))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt("password123")
        with open(enc_path, "wb") as f:
            writer.write(f)
        return enc_path

    def test_compress_pdf_alta_calidad(self, pdf_with_image, tmp_path):
        """Comprime en nivel alta y verifica que no falle y el archivo final exista."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "compressed_alta.pdf"
        
        result = compress_pdf(
            input_path=pdf_with_image,
            output_path=output,
            quality="alta"
        )
        
        assert output.exists()
        assert result["original_size"] > 0
        assert result["compressed_size"] > 0
        assert "reduction_percent" in result

    def test_compress_pdf_media_calidad(self, pdf_with_image, tmp_path):
        """Comprime en nivel media y verifica que reduzca el tamaño del archivo con imágenes."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "compressed_media.pdf"
        
        result = compress_pdf(
            input_path=pdf_with_image,
            output_path=output,
            quality="media"
        )
        
        assert output.exists()
        # En nivel media, la resolución baja a 150 DPI y se comprime como JPEG,
        # lo que debería reducir significativamente el tamaño del PDF generado por Pillow.
        assert result["compressed_size"] < result["original_size"]
        assert result["reduction_percent"] > 0
        assert result["already_optimized"] is False

    def test_compress_pdf_retorna_metricas(self, pdf_with_image, tmp_path):
        """Verifica que el diccionario resultante contenga las métricas correspondientes."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "compressed_metrics.pdf"
        
        result = compress_pdf(
            input_path=pdf_with_image,
            output_path=output,
            quality="alta"
        )
        
        assert "original_size" in result
        assert "compressed_size" in result
        assert "reduction_percent" in result
        assert "already_optimized" in result

    def test_compress_pdf_already_optimized(self, pdf_3pages, tmp_path):
        """Verifica que un PDF ya optimizado sea manejado adecuadamente sin inflar su tamaño."""
        from core.pdf_compress import compress_pdf
        # Un PDF vacío/blanco de 3 páginas ya está muy optimizado y la compresión no lo reducirá.
        output = tmp_path / "compressed_empty.pdf"
        
        result = compress_pdf(
            input_path=pdf_3pages,
            output_path=output,
            quality="baja"
        )
        
        assert output.exists()
        assert result["already_optimized"] is True
        assert result["reduction_percent"] == 0.0
        assert result["compressed_size"] == result["original_size"]

    def test_compress_pdf_protegido_lanza_error(self, encrypted_pdf, tmp_path):
        """Verifica que se lance un PermissionError claro ante PDFs cifrados."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "compressed_encrypted.pdf"
        
        with pytest.raises(PermissionError) as exc_info:
            compress_pdf(
                input_path=encrypted_pdf,
                output_path=output,
                quality="media"
            )
        assert "protegido con contraseña" in str(exc_info.value)

    def test_compress_pdf_limpia_output_en_error(self, pdf_3pages, tmp_path):
        """Asegura que los archivos intermedios o corruptos sean eliminados si ocurre un error."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "wont_exist.pdf"
        
        # Provocar error pasando un tipo de calidad inexistente
        with pytest.raises(Exception):
            compress_pdf(
                input_path=pdf_3pages,
                output_path=output,
                quality="calidad_invalida"
            )
        
        assert not output.exists()

    def test_compress_pdf_progress_callback(self, pdf_with_image, tmp_path):
        """Asegura que el callback de progreso sea invocado proporcionalmente con valores de 0 a 1."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "compressed_progress.pdf"
        
        progress_calls = []
        def progress_cb(val, msg):
            progress_calls.append((val, msg))
            
        compress_pdf(
            input_path=pdf_with_image,
            output_path=output,
            quality="alta",
            progress_callback=progress_cb
        )
        
        assert len(progress_calls) > 0
        # Verificar que el progreso comience bajo y termine en 1.0 (100%)
        assert progress_calls[0][0] <= 0.1
        assert progress_calls[-1][0] == 1.0

    def test_has_transparency(self):
        from core.pdf_compress import has_transparency
        img_opaque = Image.new("RGB", (10, 10), color="red")
        assert not has_transparency(img_opaque)

        img_transparent = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        assert has_transparency(img_transparent)

    def test_is_almost_grayscale(self):
        from core.pdf_compress import is_almost_grayscale
        img_gray = Image.new("L", (10, 10), color=128)
        assert is_almost_grayscale(img_gray)

        img_color = Image.new("RGB", (10, 10), color="red")
        assert not is_almost_grayscale(img_color)

    def test_scale_image_resolution(self):
        from core.pdf_compress import scale_image_resolution
        img = Image.new("RGB", (800, 800), color="blue")
        res = scale_image_resolution(img, 50)
        assert res.width < 800

    def test_compress_pdf_baja_calidad(self, pdf_with_image, tmp_path):
        """Comprime en nivel baja y verifica la compresión agresiva."""
        from core.pdf_compress import compress_pdf
        output = tmp_path / "compressed_baja.pdf"
        
        result = compress_pdf(
            input_path=pdf_with_image,
            output_path=output,
            quality="baja"
        )
        
        assert output.exists()
        assert result["compressed_size"] < result["original_size"]
        assert result["reduction_percent"] > 0
        assert result["already_optimized"] is False
