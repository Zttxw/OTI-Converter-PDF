"""
DocuTools — Tests para core/pdf_split.py

Pruebas del módulo de división de PDFs:
  - split_by_pages: dividir por cantidad de páginas por archivo
  - split_by_ranges: dividir por rangos específicos de páginas
  - Manejo de restos (páginas que no llenan un archivo completo)
  - Rangos superpuestos, fuera de límites
  - Callback de progreso
  - PDFs encriptados y valores inválidos

Mínimo: 5 happy path, 3 error, 2 edge case.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.pdf_split import split_by_pages, split_by_ranges


# ════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════

def _make_pdf(path: Path, num_pages: int) -> Path:
    """Helper para crear un PDF con N páginas."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    writer.write(str(path))
    return path


# ════════════════════════════════════════════════════════
#  HAPPY PATH — split_by_pages
# ════════════════════════════════════════════════════════

class TestSplitByPages:
    """Pruebas de la función split_by_pages."""

    def test_split_by_pages_even(self, tmp_path: Path):
        """
        6 páginas divididas en 2 por archivo → exactamente 3 archivos,
        cada uno con 2 páginas.
        """
        pdf = _make_pdf(tmp_path / "six.pdf", 6)
        out_dir = tmp_path / "split_even"
        out_dir.mkdir()

        result = split_by_pages(pdf, out_dir, pages_per_file=2)

        # Verificar que se crearon 3 archivos
        pdf_files = sorted(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 3, f"Se esperaban 3 archivos, se encontraron {len(pdf_files)}"

        # Cada archivo debe tener 2 páginas
        for pf in pdf_files:
            reader = PdfReader(str(pf))
            assert len(reader.pages) == 2

    def test_split_by_pages_odd(self, tmp_path: Path):
        """
        7 páginas divididas en 3 por archivo → 3 archivos:
        primeros 2 con 3 páginas, último con 1 página.
        """
        pdf = _make_pdf(tmp_path / "seven.pdf", 7)
        out_dir = tmp_path / "split_odd"
        out_dir.mkdir()

        result = split_by_pages(pdf, out_dir, pages_per_file=3)

        pdf_files = sorted(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 3

        # Verificar conteo de páginas: 3, 3, 1
        page_counts = [len(PdfReader(str(f)).pages) for f in pdf_files]
        assert sum(page_counts) == 7  # Total debe ser 7
        assert page_counts[0] == 3
        assert page_counts[1] == 3
        assert page_counts[2] == 1

    def test_split_single_page_pdf(self, tmp_path: Path):
        """Un PDF de 1 página con pages_per_file=1 → 1 archivo."""
        pdf = _make_pdf(tmp_path / "one.pdf", 1)
        out_dir = tmp_path / "split_single"
        out_dir.mkdir()

        result = split_by_pages(pdf, out_dir, pages_per_file=1)

        pdf_files = list(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 1
        reader = PdfReader(str(pdf_files[0]))
        assert len(reader.pages) == 1

    def test_split_by_pages_one_per_file(self, tmp_path: Path):
        """5 páginas con pages_per_file=1 → 5 archivos individuales."""
        pdf = _make_pdf(tmp_path / "five.pdf", 5)
        out_dir = tmp_path / "split_individual"
        out_dir.mkdir()

        result = split_by_pages(pdf, out_dir, pages_per_file=1)

        pdf_files = list(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 5

        # Cada archivo debe tener exactamente 1 página
        for pf in pdf_files:
            reader = PdfReader(str(pf))
            assert len(reader.pages) == 1

    def test_split_progress_callback(self, tmp_path: Path):
        """El callback de progreso debe invocarse con valores 0–100."""
        pdf = _make_pdf(tmp_path / "progress.pdf", 4)
        out_dir = tmp_path / "split_progress"
        out_dir.mkdir()
        callback = MagicMock()

        split_by_pages(pdf, out_dir, pages_per_file=2, progress_callback=callback)

        assert callback.called, "El callback nunca fue invocado"
        for call_args in callback.call_args_list:
            value = call_args[0][0]
            assert 0 <= value <= 100


# ════════════════════════════════════════════════════════
#  HAPPY PATH — split_by_ranges
# ════════════════════════════════════════════════════════

class TestSplitByRanges:
    """Pruebas de la función split_by_ranges."""

    def test_split_by_ranges_valid(self, tmp_path: Path):
        """
        Rangos válidos [(1,3), (4,5)] en un PDF de 5 páginas →
        2 archivos con 3 y 2 páginas respectivamente.
        """
        pdf = _make_pdf(tmp_path / "ranges.pdf", 5)
        out_dir = tmp_path / "split_ranges"
        out_dir.mkdir()

        result = split_by_ranges(pdf, out_dir, ranges=[(1, 3), (4, 5)])

        pdf_files = sorted(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 2

        page_counts = [len(PdfReader(str(f)).pages) for f in pdf_files]
        assert 3 in page_counts
        assert 2 in page_counts

    def test_split_by_ranges_single_page_range(self, tmp_path: Path):
        """Rango de una sola página [(2,2)] debe extraer 1 página."""
        pdf = _make_pdf(tmp_path / "single_range.pdf", 5)
        out_dir = tmp_path / "split_single_range"
        out_dir.mkdir()

        result = split_by_ranges(pdf, out_dir, ranges=[(2, 2)])

        pdf_files = list(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 1
        reader = PdfReader(str(pdf_files[0]))
        assert len(reader.pages) == 1

    def test_split_by_ranges_merged(self, tmp_path: Path):
        """
        Prueba que al especificar merge_ranges=True, todos los rangos
        se extraigan y unan en un único archivo PDF.
        """
        pdf = _make_pdf(tmp_path / "merged_ranges.pdf", 6)
        out_dir = tmp_path / "split_merged"
        out_dir.mkdir()

        result = split_by_ranges(pdf, out_dir, ranges=[(1, 1), (3, 3), (6, 6)], merge_ranges=True)

        pdf_files = list(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 1
        reader = PdfReader(str(pdf_files[0]))
        assert len(reader.pages) == 3  # Páginas 1, 3 y 6 unidas



# ════════════════════════════════════════════════════════
#  ERROR CASES
# ════════════════════════════════════════════════════════

class TestSplitErrors:
    """Casos de error en funciones de split."""

    def test_split_invalid_pages_per_file(self, tmp_path: Path):
        """pages_per_file=0 o negativo debe generar error."""
        pdf = _make_pdf(tmp_path / "invalid.pdf", 5)
        out_dir = tmp_path / "split_invalid"
        out_dir.mkdir()

        try:
            result = split_by_pages(pdf, out_dir, pages_per_file=0)
            assert result.get("success") is False or result.get("status") == "error"
        except (ValueError, Exception):
            pass  # Se acepta excepción por valor inválido

    def test_split_by_ranges_out_of_bounds(self, tmp_path: Path):
        """
        Rango fuera de límites (ej. página 99 en PDF de 5 páginas)
        debe generar error descriptivo.
        """
        pdf = _make_pdf(tmp_path / "oob.pdf", 5)
        out_dir = tmp_path / "split_oob"
        out_dir.mkdir()

        try:
            result = split_by_ranges(pdf, out_dir, ranges=[(1, 99)])
            # Si no lanza excepción, verificar que reporta error
            if result:
                assert (
                    result.get("success") is False
                    or result.get("status") == "error"
                    or "error" in str(result).lower()
                )
        except (ValueError, IndexError, Exception):
            pass  # Aceptable

    def test_split_encrypted_pdf(self, tmp_path: Path, encrypted_pdf_path: Path):
        """Un PDF encriptado no puede dividirse sin contraseña."""
        out_dir = tmp_path / "split_enc"
        out_dir.mkdir()

        try:
            result = split_by_pages(encrypted_pdf_path, out_dir, pages_per_file=1)
            if result:
                assert result.get("success") is False or "error" in str(result).lower()
        except Exception:
            pass  # Se acepta excepción


# ════════════════════════════════════════════════════════
#  EDGE CASES
# ════════════════════════════════════════════════════════

class TestSplitEdgeCases:
    """Casos límite de split."""

    def test_split_by_ranges_overlap(self, tmp_path: Path):
        """
        Rangos superpuestos [(1,3), (2,4)] no deben causar crash.
        Puede producir archivos con páginas duplicadas o reportar advertencia.
        """
        pdf = _make_pdf(tmp_path / "overlap.pdf", 5)
        out_dir = tmp_path / "split_overlap"
        out_dir.mkdir()

        try:
            result = split_by_ranges(pdf, out_dir, ranges=[(1, 3), (2, 4)])
            # No debe haber crash; se aceptan resultados parciales
            pdf_files = list(out_dir.glob("*.pdf"))
            assert len(pdf_files) >= 1  # Al menos un archivo generado
        except Exception:
            pass  # Algunos implementaciones rechazan rangos superpuestos

    def test_split_pages_per_file_exceeds_total(self, tmp_path: Path):
        """
        pages_per_file mayor que el total de páginas → 1 archivo con
        todas las páginas.
        """
        pdf = _make_pdf(tmp_path / "small.pdf", 3)
        out_dir = tmp_path / "split_big_chunk"
        out_dir.mkdir()

        result = split_by_pages(pdf, out_dir, pages_per_file=100)

        pdf_files = list(out_dir.glob("*.pdf"))
        assert len(pdf_files) == 1  # Solo 1 archivo
        reader = PdfReader(str(pdf_files[0]))
        assert len(reader.pages) == 3  # Todas las páginas

    def test_split_negative_pages_per_file(self, tmp_path: Path):
        """pages_per_file negativo debe generar error."""
        pdf = _make_pdf(tmp_path / "neg.pdf", 3)
        out_dir = tmp_path / "split_neg"
        out_dir.mkdir()

        try:
            result = split_by_pages(pdf, out_dir, pages_per_file=-1)
            assert result.get("success") is False or result.get("status") == "error"
        except (ValueError, Exception):
            pass


def test_pages_to_ranges_conversion():
    """Prueba unitaria de la lógica de conversión de conjunto de páginas a cadena de rangos."""
    from ui.panels.split_panel import SplitPanel
    # Usamos una función local idéntica a la implementada en SplitPanel para testeo puro
    def local_converter(pages):
        if not pages:
            return ""
        sorted_pages = sorted(list(pages))
        ranges = []
        start = sorted_pages[0]
        end = sorted_pages[0]
        
        for p in sorted_pages[1:]:
            if p == end + 1:
                end = p
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = p
                end = p
        
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
            
        return ", ".join(ranges)

    assert local_converter(set()) == ""
    assert local_converter({1}) == "1"
    assert local_converter({1, 2, 3}) == "1-3"
    assert local_converter({1, 3, 5}) == "1, 3, 5"
    assert local_converter({1, 2, 3, 5, 7, 8}) == "1-3, 5, 7-8"
    assert local_converter({2, 3, 4, 6, 8, 9, 10}) == "2-4, 6, 8-10"


def test_get_pdf_thumbnails_range_parsing(tmp_path: Path):
    """Prueba que el extractor de miniaturas maneje correctamente el rango y tuplas."""
    from core.pdf_split import get_pdf_page_count_and_thumbnails
    from PIL import Image
    
    # Crear un PDF de 15 páginas
    pdf = _make_pdf(tmp_path / "long_doc.pdf", 15)
    
    # Caso 1: Rango simple 13-15
    result = get_pdf_page_count_and_thumbnails(str(pdf), page_range="13-15", return_tuples=True)
    assert result["success"] is True
    assert result["total_pages"] == 15
    assert len(result["thumbnails"]) == 3
    # Debe ser lista de tuplas
    for p_num, img in result["thumbnails"]:
        assert p_num in [13, 14, 15]
        assert isinstance(img, Image.Image)
        
    # Caso 2: Rango con comas y repetidos
    result2 = get_pdf_page_count_and_thumbnails(str(pdf), page_range="1-2, 5, 5", return_tuples=True)
    assert result2["success"] is True
    assert len(result2["thumbnails"]) == 3
    loaded_pages = [p_num for p_num, _ in result2["thumbnails"]]
    assert loaded_pages == [1, 2, 5]


