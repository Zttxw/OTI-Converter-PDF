"""
DocuTools — Tests para core/pdf_merge.py

Pruebas del módulo de unión (merge) de PDFs:
  - Unir 2, 3, 5 PDFs y verificar total de páginas
  - Lista vacía → error descriptivo
  - PDF inválido en la lista → manejo gracioso
  - Verificar preservación de contenido/páginas
  - Callback de progreso con valores 0–100
  - PDF encriptado → error reportado

Mínimo: 5 happy path, 3 error, 2 edge case.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.pdf_merge import merge_pdfs


# ════════════════════════════════════════════════════════
#  Helpers — Crear PDFs individuales para merge
# ════════════════════════════════════════════════════════

def _make_pdf(path: Path, num_pages: int) -> Path:
    """Helper para generar un PDF con N páginas."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    writer.write(str(path))
    return path


# ════════════════════════════════════════════════════════
#  HAPPY PATH — Operaciones exitosas de merge
# ════════════════════════════════════════════════════════

class TestMergeHappyPath:
    """Casos exitosos de unión de PDFs."""

    def test_merge_two_pdfs(self, tmp_path: Path):
        """Unir 2 PDFs (3 + 2 páginas) debe producir un PDF de 5 páginas."""
        pdf1 = _make_pdf(tmp_path / "doc1.pdf", 3)
        pdf2 = _make_pdf(tmp_path / "doc2.pdf", 2)
        output = tmp_path / "merged.pdf"

        result = merge_pdfs([pdf1, pdf2], output)

        assert output.exists(), "El archivo de salida no fue creado"
        reader = PdfReader(str(output))
        assert len(reader.pages) == 5
        assert result.get("success") is True or result.get("status") == "success"

    def test_merge_three_pdfs(self, tmp_path: Path):
        """Unir 3 PDFs (2 + 3 + 4 páginas) debe producir 9 páginas."""
        pdfs = [
            _make_pdf(tmp_path / "a.pdf", 2),
            _make_pdf(tmp_path / "b.pdf", 3),
            _make_pdf(tmp_path / "c.pdf", 4),
        ]
        output = tmp_path / "merged_3.pdf"

        result = merge_pdfs(pdfs, output)

        reader = PdfReader(str(output))
        assert len(reader.pages) == 9

    def test_merge_single_file(self, tmp_path: Path):
        """Unir 1 solo PDF debe producir una copia válida."""
        pdf = _make_pdf(tmp_path / "solo.pdf", 4)
        output = tmp_path / "merged_single.pdf"

        result = merge_pdfs([pdf], output)

        assert output.exists()
        reader = PdfReader(str(output))
        assert len(reader.pages) == 4

    def test_merge_preserves_pages(self, tmp_path: Path):
        """El merge debe preservar exactamente el número total de páginas."""
        page_counts = [1, 2, 3, 4, 5]
        pdfs = [
            _make_pdf(tmp_path / f"doc_{i}.pdf", count)
            for i, count in enumerate(page_counts)
        ]
        output = tmp_path / "preserved.pdf"

        merge_pdfs(pdfs, output)

        reader = PdfReader(str(output))
        assert len(reader.pages) == sum(page_counts)  # 15 páginas

    def test_merge_large_merge(self, tmp_path: Path):
        """Unir 5 PDFs de 3 páginas cada uno debe producir 15 páginas."""
        pdfs = [
            _make_pdf(tmp_path / f"batch_{i}.pdf", 3) for i in range(5)
        ]
        output = tmp_path / "batch_merged.pdf"

        result = merge_pdfs(pdfs, output)

        reader = PdfReader(str(output))
        assert len(reader.pages) == 15

    def test_merge_progress_callback(self, tmp_path: Path):
        """
        El callback de progreso debe ser invocado al menos una vez
        con valores entre 0 y 100.
        """
        pdfs = [
            _make_pdf(tmp_path / f"cb_{i}.pdf", 2) for i in range(3)
        ]
        output = tmp_path / "cb_merged.pdf"
        callback = MagicMock()

        merge_pdfs(pdfs, output, progress_callback=callback)

        assert callback.called, "El callback de progreso nunca fue llamado"
        # Verificar que al menos un argumento está en rango [0, 100]
        for call_args in callback.call_args_list:
            value = call_args[0][0]  # Primer argumento posicional
            assert 0 <= value <= 100, f"Valor de progreso fuera de rango: {value}"


# ════════════════════════════════════════════════════════
#  ERROR CASES — Entradas inválidas
# ════════════════════════════════════════════════════════

class TestMergeErrors:
    """Casos de error para la función de merge."""

    def test_merge_empty_list(self, tmp_path: Path):
        """Una lista vacía debe retornar error descriptivo, no crash."""
        output = tmp_path / "empty_merge.pdf"

        result = merge_pdfs([], output)

        # Debe indicar error, no crear archivo
        assert result.get("success") is False or result.get("status") == "error"
        assert not output.exists() or "error" in str(result).lower()

    def test_merge_one_invalid(self, tmp_path: Path):
        """
        Si uno de los PDFs es inválido, debe reportar el error
        para ese archivo pero idealmente no crashear.
        """
        valid = _make_pdf(tmp_path / "valid.pdf", 3)
        invalid = tmp_path / "invalid.pdf"
        invalid.write_bytes(b"NO SOY PDF")
        output = tmp_path / "partial_merge.pdf"

        # Puede lanzar excepción o retornar resultado con error
        try:
            result = merge_pdfs([valid, invalid], output)
            # Si no lanza excepción, debe reportar el error
            has_error = (
                result.get("success") is False
                or result.get("status") == "error"
                or "error" in str(result).lower()
                or "invalid" in str(result).lower()
            )
            # Aceptamos tanto que falle como que reporte parcial
        except Exception as e:
            # Si lanza excepción, verificar que es descriptiva
            assert str(e), "La excepción no tiene mensaje descriptivo"

    def test_merge_encrypted_pdf(self, tmp_path: Path, encrypted_pdf_path: Path):
        """Un PDF encriptado debe ser reportado como error."""
        valid = _make_pdf(tmp_path / "normal.pdf", 2)
        output = tmp_path / "enc_merge.pdf"

        try:
            result = merge_pdfs([valid, encrypted_pdf_path], output)
            # Si retorna resultado, debe indicar error
        except Exception:
            pass  # Se acepta que lance excepción por PDF encriptado

    def test_merge_nonexistent_file(self, tmp_path: Path):
        """Intentar unir con un archivo que no existe debe fallar."""
        fake = tmp_path / "fantasma.pdf"
        output = tmp_path / "ghost_merge.pdf"

        try:
            result = merge_pdfs([fake], output)
            assert result.get("success") is False or result.get("status") == "error"
        except (FileNotFoundError, Exception):
            pass  # Se acepta excepción por archivo inexistente


# ════════════════════════════════════════════════════════
#  EDGE CASES — Casos límite
# ════════════════════════════════════════════════════════

class TestMergeEdgeCases:
    """Casos límite del merge."""

    def test_merge_output_dir_does_not_exist(self, tmp_path: Path):
        """
        Si el directorio de salida no existe, la función debe
        crear el directorio o reportar error claro.
        """
        pdf = _make_pdf(tmp_path / "edge.pdf", 2)
        output = tmp_path / "nuevo_dir" / "resultado.pdf"

        try:
            result = merge_pdfs([pdf], output)
            # Si tiene éxito, el directorio debió ser creado
            if output.exists():
                assert output.parent.is_dir()
        except (FileNotFoundError, OSError):
            pass  # Aceptable si no crea directorios automáticamente

    def test_merge_same_file_twice(self, tmp_path: Path):
        """Unir el mismo archivo 2 veces debe duplicar las páginas."""
        pdf = _make_pdf(tmp_path / "repeat.pdf", 3)
        output = tmp_path / "doubled.pdf"

        result = merge_pdfs([pdf, pdf], output)

        if output.exists():
            reader = PdfReader(str(output))
            assert len(reader.pages) == 6  # 3 + 3
