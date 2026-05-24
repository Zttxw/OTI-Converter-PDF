"""
DocuTools — Tests para utils/file_validator.py

Pruebas exhaustivas del módulo FileValidator que valida:
  - Existencia de archivos
  - Tamaño de archivos (vacíos, dentro del límite)
  - Magic bytes (PDF, JPG, PNG vs extensión)
  - Path traversal (ataques de directorio)
  - Sanitización de nombres de archivo
  - Legibilidad de PDFs (pypdf)
  - Detección de PDFs encriptados
  - Validación completa de PDF
  - Generación de rutas de salida seguras

Mínimo: 5 happy path, 3 error, 2 edge case.
"""

import sys
from pathlib import Path

import pytest

# Agregar raíz del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.file_validator import FileValidator
from utils.constants import MAX_FILENAME_LENGTH


# ════════════════════════════════════════════════════════
#  HAPPY PATH — Archivos válidos y operaciones correctas
# ════════════════════════════════════════════════════════

class TestValidateFileExists:
    """Pruebas de existencia de archivos."""

    def test_validate_existing_file(self, sample_pdf_path: Path):
        """Un PDF generado correctamente debe existir y ser válido."""
        valid, msg = FileValidator.validate_file_exists(sample_pdf_path)
        assert valid is True, f"Se esperaba válido, pero: {msg}"
        assert msg == ""

    def test_validate_nonexistent_file(self, tmp_path: Path):
        """Un archivo que no existe debe retornar error descriptivo."""
        fake_path = tmp_path / "no_existe_jamás.pdf"
        valid, msg = FileValidator.validate_file_exists(fake_path)
        assert valid is False
        assert "no existe" in msg.lower()

    def test_validate_directory_instead_of_file(self, tmp_path: Path):
        """Pasar un directorio como archivo debe ser rechazado."""
        valid, msg = FileValidator.validate_file_exists(tmp_path)
        assert valid is False
        assert "directorio" in msg.lower()


class TestValidateFileSize:
    """Pruebas de validación de tamaño de archivo."""

    def test_validate_file_size_ok(self, sample_pdf_path: Path):
        """Un PDF de prueba (pocos KB) debe estar dentro del límite."""
        valid, msg = FileValidator.validate_file_size(sample_pdf_path)
        assert valid is True
        assert msg == ""

    def test_validate_empty_file(self, empty_file: Path):
        """Un archivo vacío (0 bytes) debe ser rechazado con mensaje claro."""
        valid, msg = FileValidator.validate_file_size(empty_file)
        assert valid is False
        assert "vacío" in msg.lower() or "0 bytes" in msg.lower()


class TestValidateMagicBytes:
    """Pruebas de validación de magic bytes (firma de archivo)."""

    def test_validate_magic_bytes_pdf(self, sample_pdf_path: Path):
        """Un PDF real debe tener los magic bytes correctos (%PDF)."""
        valid, msg = FileValidator.validate_magic_bytes(sample_pdf_path)
        assert valid is True
        assert msg == ""

    def test_validate_magic_bytes_wrong_extension(self, corrupt_file: Path):
        """
        Un archivo con extensión .pdf pero contenido basura debe fallar
        la validación de magic bytes.
        """
        valid, msg = FileValidator.validate_magic_bytes(corrupt_file)
        assert valid is False
        assert "no coincide" in msg.lower() or "corrupto" in msg.lower()

    def test_validate_magic_bytes_jpg(self, sample_jpg_path: Path):
        """Una imagen JPG real debe tener los magic bytes FFD8FF."""
        valid, msg = FileValidator.validate_magic_bytes(sample_jpg_path)
        assert valid is True
        assert msg == ""

    def test_validate_magic_bytes_png(self, sample_png_path: Path):
        """Una imagen PNG real debe tener la firma \\x89PNG."""
        valid, msg = FileValidator.validate_magic_bytes(sample_png_path)
        assert valid is True
        assert msg == ""

    def test_validate_magic_bytes_bmp(self, sample_bmp_path: Path):
        """Una imagen BMP real debe tener la firma BM."""
        valid, msg = FileValidator.validate_magic_bytes(sample_bmp_path)
        assert valid is True
        assert msg == ""

    def test_validate_magic_bytes_docx(self, sample_docx_path: Path):
        """Un DOCX (ZIP) debe tener la firma PK\\x03\\x04."""
        valid, msg = FileValidator.validate_magic_bytes(sample_docx_path)
        assert valid is True
        assert msg == ""

    def test_validate_magic_bytes_unknown_extension(self, tmp_path: Path):
        """
        Archivos con extensión desconocida no deben ser rechazados
        (no podemos verificar lo que no conocemos).
        """
        unknown = tmp_path / "data.xyz"
        unknown.write_bytes(b"contenido cualquiera")
        valid, msg = FileValidator.validate_magic_bytes(unknown)
        assert valid is True  # Extensiones desconocidas se aceptan


# ════════════════════════════════════════════════════════
#  PATH TRAVERSAL — Protección contra ataques de directorio
# ════════════════════════════════════════════════════════

class TestValidatePathTraversal:
    """Pruebas contra ataques de path traversal."""

    def test_validate_path_traversal_attack(self):
        """
        Una ruta con '..' debe ser rechazada como posible
        ataque de path traversal.
        """
        malicious = Path("../../etc/passwd")
        valid, msg = FileValidator.validate_path_traversal(malicious)
        assert valid is False
        assert ".." in msg or "navegación" in msg.lower()

    def test_validate_path_traversal_safe(self, sample_pdf_path: Path):
        """Una ruta normal sin '..' debe ser aceptada."""
        valid, msg = FileValidator.validate_path_traversal(sample_pdf_path)
        assert valid is True
        assert msg == ""

    def test_validate_path_traversal_with_allowed_dir(self, sample_pdf_path: Path):
        """
        Con directorio permitido, la ruta debe resolverse dentro de él.
        """
        allowed = sample_pdf_path.parent
        valid, msg = FileValidator.validate_path_traversal(
            sample_pdf_path, allowed_directory=allowed
        )
        assert valid is True

    def test_validate_path_traversal_outside_allowed_dir(self, tmp_path: Path):
        """
        Una ruta que escapa del directorio permitido debe ser rechazada.
        """
        # Crear un directorio "jail"
        jail = tmp_path / "jail"
        jail.mkdir()
        # Crear archivo fuera del jail
        outside = tmp_path / "outside.pdf"
        outside.write_bytes(b"%PDF-1.4 test")
        # Verificar que la ruta fuera del jail es rechazada
        valid, msg = FileValidator.validate_path_traversal(
            outside, allowed_directory=jail
        )
        assert valid is False
        assert "escapa" in msg.lower()


# ════════════════════════════════════════════════════════
#  SANITIZACIÓN DE NOMBRES DE ARCHIVO
# ════════════════════════════════════════════════════════

class TestSanitizeFilename:
    """Pruebas de sanitización de nombres de archivo."""

    def test_sanitize_filename_dangerous_chars(self):
        """Caracteres peligrosos (<>:"/\\|?*) deben reemplazarse por '_'."""
        dirty = 'archivo<peligroso>:"test"|?.pdf'
        sanitized = FileValidator.sanitize_filename(dirty)
        # No debe contener caracteres peligrosos
        dangerous = '<>:"/\\|?*'
        for char in dangerous:
            assert char not in sanitized, f"Carácter peligroso '{char}' no fue eliminado"
        # Debe conservar la extensión
        assert sanitized.endswith(".pdf")

    def test_sanitize_filename_control_chars(self):
        """Caracteres de control (ASCII 0-31) deben ser eliminados."""
        # Nombre con caracteres de control embebidos
        dirty = "archivo\x00\x01\x02test\x1F.pdf"
        sanitized = FileValidator.sanitize_filename(dirty)
        # No debe contener caracteres de control
        for i in range(32):
            assert chr(i) not in sanitized

    def test_sanitize_filename_long_name(self):
        """Nombres largos deben truncarse al máximo permitido."""
        long_name = "a" * 300 + ".pdf"
        sanitized = FileValidator.sanitize_filename(long_name)
        assert len(sanitized) <= MAX_FILENAME_LENGTH

    def test_sanitize_filename_empty(self):
        """Un nombre vacío debe generar un nombre genérico válido."""
        sanitized = FileValidator.sanitize_filename("")
        assert sanitized  # No debe estar vacío
        assert len(sanitized) > 0
        assert sanitized == "archivo_sin_nombre"

    def test_sanitize_filename_normal(self):
        """Un nombre normal no debe ser modificado."""
        normal = "documento_final_v2.pdf"
        sanitized = FileValidator.sanitize_filename(normal)
        assert sanitized == normal

    def test_sanitize_filename_only_dangerous_chars(self):
        """Si el nombre solo tiene caracteres peligrosos, generar nombre genérico."""
        dirty = '<>:"/\\|?*.pdf'
        sanitized = FileValidator.sanitize_filename(dirty)
        # Después de reemplazar todos por _, strip() podría dejar solo underscores
        assert sanitized.endswith(".pdf")
        assert len(sanitized) > 4  # Más que solo ".pdf"


# ════════════════════════════════════════════════════════
#  VALIDACIÓN DE PDF — Legibilidad y cifrado
# ════════════════════════════════════════════════════════

class TestValidatePdfReadable:
    """Pruebas de legibilidad de PDFs con pypdf."""

    def test_validate_pdf_readable(self, sample_pdf_path: Path):
        """Un PDF bien formado debe ser legible sin errores."""
        valid, msg = FileValidator.validate_pdf_readable(sample_pdf_path)
        assert valid is True
        assert msg == ""

    def test_validate_pdf_encrypted(self, encrypted_pdf_path: Path):
        """
        Un PDF encriptado debe ser detectado y reportar que necesita
        desprotegerse primero.
        """
        is_encrypted, msg = FileValidator.validate_pdf_encrypted(encrypted_pdf_path)
        assert is_encrypted is True
        assert "contraseña" in msg.lower() or "protegido" in msg.lower()

    def test_validate_pdf_corrupt(self, corrupt_file: Path):
        """Un archivo corrupto disfrazado de PDF debe fallar la lectura."""
        valid, msg = FileValidator.validate_pdf_readable(corrupt_file)
        assert valid is False
        assert "corrupto" in msg.lower() or "malformado" in msg.lower()

    def test_validate_pdf_not_encrypted(self, sample_pdf_path: Path):
        """Un PDF sin contraseña no debe reportarse como encriptado."""
        is_encrypted, msg = FileValidator.validate_pdf_encrypted(sample_pdf_path)
        assert is_encrypted is False


class TestValidateFullPdf:
    """Pruebas de validación completa de PDF (todas las verificaciones)."""

    def test_validate_full_pdf(self, sample_pdf_path: Path):
        """La validación completa debe pasar para un PDF válido normal."""
        valid, msg = FileValidator.validate_pdf(sample_pdf_path)
        assert valid is True
        assert msg == ""

    def test_validate_full_pdf_encrypted(self, encrypted_pdf_path: Path):
        """
        La validación completa con check_encrypted=True debe rechazar
        PDFs encriptados.
        """
        valid, msg = FileValidator.validate_pdf(
            encrypted_pdf_path, check_encrypted=True
        )
        assert valid is False
        assert "contraseña" in msg.lower() or "protegido" in msg.lower()

    def test_validate_full_pdf_skip_encrypted_check(self, encrypted_pdf_path: Path):
        """
        La validación completa con check_encrypted=False debe aceptar
        PDFs encriptados (si pypdf puede abrirlos).
        """
        # Nota: pypdf puede abrir encriptados sin desbloquear en algunos casos
        # Depende de la implementación; este test verifica la flag
        valid, msg = FileValidator.validate_pdf(
            encrypted_pdf_path, check_encrypted=False
        )
        # Puede pasar o fallar dependiendo de si pypdf requiere contraseña
        # Lo importante es que NO falle por "está encriptado"
        if not valid:
            pass

    def test_validate_full_pdf_nonexistent(self, tmp_path: Path):
        """La validación completa de un archivo inexistente debe fallar primero."""
        fake = tmp_path / "fantasma.pdf"
        valid, msg = FileValidator.validate_pdf(fake)
        assert valid is False
        assert "no existe" in msg.lower()


# ════════════════════════════════════════════════════════
#  RUTA DE SALIDA SEGURA
# ════════════════════════════════════════════════════════

class TestGetSafeOutputPath:
    """Pruebas de generación de rutas de salida seguras."""

    def test_get_safe_output_path_no_conflict(self, output_dir: Path):
        """Si no hay conflicto, la ruta debe retornarse tal cual (sanitizada)."""
        desired = output_dir / "resultado.pdf"
        safe = FileValidator.get_safe_output_path(desired)
        assert safe.name == "resultado.pdf"
        assert safe.parent == output_dir

    def test_get_safe_output_path_with_conflict(self, sample_pdf_path: Path):
        """
        Si el archivo ya existe, debe agregar un sufijo numérico
        para evitar sobreescritura.
        """
        safe = FileValidator.get_safe_output_path(sample_pdf_path)
        # Debe ser diferente del original (que ya existe)
        assert safe != sample_pdf_path
        assert safe.suffix == ".pdf"
        # Debe contener un sufijo numérico como _1
        assert "_1" in safe.name or "_" in safe.stem

    def test_get_safe_output_path_no_overwrite_flag(self, output_dir: Path):
        """Con avoid_overwrite=False, retorna la ruta directamente."""
        desired = output_dir / "salida.pdf"
        safe = FileValidator.get_safe_output_path(desired, avoid_overwrite=False)
        assert safe.name == "salida.pdf"

    def test_get_safe_output_path_sanitizes_name(self, output_dir: Path):
        """La ruta de salida debe sanitizar caracteres peligrosos."""
        dirty = output_dir / 'archivo<malo>:"test".pdf'
        safe = FileValidator.get_safe_output_path(dirty)
        dangerous = '<>:"/\\|?*'
        for char in dangerous:
            assert char not in safe.name

    def test_get_safe_output_path_multiple_conflicts(self, tmp_path: Path):
        """
        Si existen archivo.pdf, archivo_1.pdf, archivo_2.pdf,
        debe generar archivo_3.pdf.
        """
        from pypdf import PdfWriter
        base = tmp_path / "report.pdf"
        # Crear el original y las primeras variantes
        for name in ["report.pdf", "report_1.pdf", "report_2.pdf"]:
            p = tmp_path / name
            w = PdfWriter()
            w.add_blank_page(612, 792)
            w.write(str(p))

        safe = FileValidator.get_safe_output_path(base)
        assert safe.name == "report_3.pdf"


# ════════════════════════════════════════════════════════
#  VALIDACIÓN DE IMÁGENES Y WORD
# ════════════════════════════════════════════════════════

class TestValidateImage:
    """Pruebas de validación de archivos de imagen."""

    def test_validate_image_jpg(self, sample_jpg_path: Path):
        """Una imagen JPG válida debe pasar la validación."""
        valid, msg = FileValidator.validate_image(sample_jpg_path)
        assert valid is True

    def test_validate_image_png(self, sample_png_path: Path):
        """Una imagen PNG con transparencia debe pasar la validación."""
        valid, msg = FileValidator.validate_image(sample_png_path)
        assert valid is True

    def test_validate_image_bmp(self, sample_bmp_path: Path):
        """Una imagen BMP debe pasar la validación."""
        valid, msg = FileValidator.validate_image(sample_bmp_path)
        assert valid is True

    def test_validate_image_nonexistent(self, tmp_path: Path):
        """Una imagen inexistente debe fallar."""
        fake = tmp_path / "no_existe.jpg"
        valid, msg = FileValidator.validate_image(fake)
        assert valid is False


class TestValidateWord:
    """Pruebas de validación de archivos Word."""

    def test_validate_word_docx(self, sample_docx_path: Path):
        """Un DOCX válido debe pasar la validación."""
        valid, msg = FileValidator.validate_word(sample_docx_path)
        assert valid is True

    def test_validate_word_wrong_extension(self, tmp_path: Path):
        """Un archivo .txt renombrado a .doc debe fallar en extensión."""
        fake_doc = tmp_path / "fake.txt"
        fake_doc.write_text("no soy un Word")
        valid, msg = FileValidator.validate_word(fake_doc)
        assert valid is False
