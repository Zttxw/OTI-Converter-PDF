import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

def split_by_pages(
    input_path: Path,
    output_dir: Path,
    pages_per_file: int,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """Divide un PDF en múltiples archivos de tamaño fijo de páginas."""
    from pypdf import PdfReader, PdfWriter
    
    result = {"success": False, "files_created": 0, "error": None}
    
    try:
        reader = PdfReader(str(input_path))
        total_pages = len(reader.pages)
        
        if total_pages == 0:
            result["error"] = "El documento no tiene páginas."
            return result
            
        if pages_per_file <= 0:
            result["error"] = "El número de páginas por archivo debe ser mayor a 0."
            return result

        base_name = input_path.stem
        file_count = 1
        
        for i in range(0, total_pages, pages_per_file):
            if progress_callback:
                percent = int((i / total_pages) * 100)
                progress_callback(percent, f"Creando parte {file_count}...")
                
            writer = PdfWriter()
            end_page = min(i + pages_per_file, total_pages)
            
            for j in range(i, end_page):
                writer.add_page(reader.pages[j])
                
            out_name = output_dir / f"{base_name}_parte_{file_count:03d}.pdf"
            
            # Prevenir sobreescritura
            counter = 1
            final_out = out_name
            while final_out.exists():
                final_out = output_dir / f"{base_name}_parte_{file_count:03d}_{counter}.pdf"
                counter += 1
                
            with open(final_out, "wb") as f:
                writer.write(f)
                
            file_count += 1
            result["files_created"] += 1
            
        result["success"] = True
        
    except Exception as e:
        logger.error(f"Error dividiendo por páginas: {e}")
        result["error"] = str(e)
        
    return result

def split_by_ranges(
    input_path: Path,
    output_dir: Path,
    ranges: list[tuple[int, int]],
    merge_ranges: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Divide un PDF extrayendo rangos específicos.
    ranges: lista de tuplas (inicio, fin). Indexado desde 1.
    """
    from pypdf import PdfReader, PdfWriter
    
    result = {"success": False, "files_created": 0, "error": None}
    
    try:
        reader = PdfReader(str(input_path))
        total_pages = len(reader.pages)
        
        base_name = input_path.stem
        total_ranges = len(ranges)
        
        if merge_ranges:
            if progress_callback:
                progress_callback(10, "Extrayendo y uniendo páginas...")
                
            writer = PdfWriter()
            # Añadir todas las páginas de todos los rangos al mismo writer
            for start, end in ranges:
                start_idx = max(0, start - 1)
                end_idx = min(total_pages, end)
                for j in range(start_idx, end_idx):
                    writer.add_page(reader.pages[j])
                    
            # Generar nombre representativo de los rangos
            ranges_str = "_".join(f"{s}-{e}" if s != e else f"{s}" for s, e in ranges)
            # Acortar si es extremadamente largo
            if len(ranges_str) > 50:
                ranges_str = "seleccionado"
                
            out_name = output_dir / f"{base_name}_extraido_{ranges_str}.pdf"
            
            counter = 1
            final_out = out_name
            while final_out.exists():
                final_out = output_dir / f"{base_name}_extraido_{ranges_str}_{counter}.pdf"
                counter += 1
                
            with open(final_out, "wb") as f:
                writer.write(f)
                
            result["files_created"] = 1
        else:
            for idx, (start, end) in enumerate(ranges):
                if progress_callback:
                    percent = int((idx / total_ranges) * 100)
                    progress_callback(percent, f"Extrayendo rango {start}-{end}...")
                    
                # Ajustar a indexado 0 y limitar al total real
                start_idx = max(0, start - 1)
                end_idx = min(total_pages, end)
                
                if start_idx >= total_pages or start_idx >= end_idx:
                    logger.warning(f"Rango inválido ignorado: {start}-{end}")
                    continue
                    
                writer = PdfWriter()
                for j in range(start_idx, end_idx):
                    writer.add_page(reader.pages[j])
                    
                out_name = output_dir / f"{base_name}_rango_{start}-{end}.pdf"
                
                counter = 1
                final_out = out_name
                while final_out.exists():
                    final_out = output_dir / f"{base_name}_rango_{start}-{end}_{counter}.pdf"
                    counter += 1
                    
                with open(final_out, "wb") as f:
                    writer.write(f)
                    
                result["files_created"] += 1
                
        result["success"] = True
        if result["files_created"] == 0:
            result["error"] = "No se extrajo ningún archivo válido de los rangos proporcionados."
            result["success"] = False
            
    except Exception as e:
        logger.error(f"Error dividiendo por rangos: {e}")
        result["error"] = str(e)
        
    return result

def get_pdf_page_count_and_thumbnails(
    pdf_path: str,
    page_range: Optional[str] = None,
    max_thumbnails: Optional[int] = None,
    return_tuples: bool = False
) -> dict:
    """
    Retorna el número de páginas y una lista de imágenes PIL de previsualización.
    Si return_tuples es True, retorna tuplas (numero_de_pagina, imagen_PIL) en la lista thumbnails.
    """
    import fitz
    import io
    from PIL import Image
    
    result = {"success": False, "total_pages": 0, "thumbnails": [], "error": None}
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        result["total_pages"] = total_pages
        
        # Determinar qué páginas extraer
        pages_to_load = []
        if page_range:
            parts = [p.strip() for p in page_range.split(",") if p.strip()]
            for p in parts:
                if "-" in p:
                    subparts = p.split("-")
                    if len(subparts) == 2:
                        try:
                            s = int(subparts[0].strip())
                            e = int(subparts[1].strip())
                            if s <= e:
                                for page in range(s, e + 1):
                                    if 1 <= page <= total_pages:
                                        pages_to_load.append(page)
                        except ValueError:
                            pass
                else:
                    try:
                        page = int(p.strip())
                        if 1 <= page <= total_pages:
                            pages_to_load.append(page)
                    except ValueError:
                        pass
            # Conservar orden sin duplicados
            seen = set()
            pages_to_load = [x for x in pages_to_load if not (x in seen or seen.add(x))]
        else:
            # Comportamiento heredado/retrocompatible
            limit = max_thumbnails if max_thumbnails is not None else 12
            count_to_extract = min(total_pages, limit)
            pages_to_load = list(range(1, count_to_extract + 1))
            
        # Techo de seguridad de 30 páginas para proteger rendimiento y memoria
        pages_to_load = pages_to_load[:30]
        
        for page_num in pages_to_load:
            # fitz usa indexado 0
            page = doc.load_page(page_num - 1)
            rect = page.rect
            w, h = rect.width, rect.height
            if w <= 0 or h <= 0:
                continue
            scale = 90.0 / w
            matrix = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            img.load()
            
            if return_tuples:
                result["thumbnails"].append((page_num, img))
            else:
                result["thumbnails"].append(img)
                
        doc.close()
        result["success"] = True
    except Exception as e:
        logger.error(f"Error generando miniaturas de PDF: {e}")
        result["error"] = str(e)
    return result

