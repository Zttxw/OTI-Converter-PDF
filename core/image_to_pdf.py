import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Tamaños de página en puntos (1 pulgada = 72 puntos)
_PAGE_SIZES = {
    "a4": (595.276, 841.890),       # 210mm x 297mm
    "letter": (612.0, 792.0),       # 8.5in x 11in
}

def images_to_pdf(
    input_paths: list[Path],
    output_path: Path,
    page_size: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> dict:
    """
    Convierte múltiples imágenes en un único PDF.
    Soporta varios formatos.
    """
    result = {
        "success": False,
        "output_path": None,
        "pages": 0,
        "error": None
    }
    
    if not input_paths:
        result["error"] = "No se proporcionaron imágenes."
        return result
        
    try:
        from PIL import Image
        import img2pdf
        
        processed_images = []
        temp_files = []
        total = len(input_paths)
        
        for idx, path in enumerate(input_paths):
            if progress_callback:
                percent = int((idx / total) * 40)
                progress_callback(percent, f"Procesando imagen {idx+1} de {total}...")
                
            if not path.exists():
                continue
                
            try:
                img = Image.open(path)
                
                # Convertir a RGB (eliminar canal alpha, útil para PNGs transparentes)
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        bg.paste(img, mask=img.split()[3]) # Usar alpha como máscara
                    else:
                        img = img.convert("RGBA")
                        bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Guardar en temporal optimizado para img2pdf
                temp_path = path.parent / f".tmp_oti_{idx}.jpg"
                img.save(temp_path, "JPEG", quality=95)
                temp_files.append(temp_path)
                processed_images.append(str(temp_path))
                
            except Exception as e:
                logger.error(f"Error procesando imagen {path}: {e}")
                
        if not processed_images:
            result["error"] = "Ninguna de las imágenes pudo ser procesada válidamente."
            return result
            
        if progress_callback:
            progress_callback(50, "Generando documento PDF...")
            
        # Configuraciones de layout
        ps_lower = page_size.lower() if page_size else "auto"
        
        if ps_lower in ("auto", "fit_image"):
            # Sin layout — img2pdf usa el tamaño de la imagen
            layout_fun = img2pdf.get_layout_fun(pagesize=None)
        elif ps_lower in _PAGE_SIZES:
            width_pt, height_pt = _PAGE_SIZES[ps_lower]
            layout_fun = img2pdf.get_layout_fun(
                pagesize=(
                    img2pdf.mm_to_pt(width_pt / 72 * 25.4),
                    img2pdf.mm_to_pt(height_pt / 72 * 25.4)
                )
            )
        else:
            # Fallback: sin pagesize
            layout_fun = img2pdf.get_layout_fun(pagesize=None)
        
        # Prevenir sobreescritura
        final_output = output_path
        counter = 1
        while final_output.exists():
            final_output = output_path.parent / f"{output_path.stem}_{counter}{output_path.suffix}"
            counter += 1
            
        if progress_callback:
            progress_callback(80, "Escribiendo archivo a disco...")
            
        with open(final_output, "wb") as f:
            img2pdf.convert(processed_images, outputstream=f, layout_fun=layout_fun)
            
        result["success"] = True
        result["output_path"] = str(final_output)
        result["pages"] = len(processed_images)
        
    except Exception as e:
        logger.error(f"Error convirtiendo imágenes a PDF: {e}")
        result["error"] = str(e)
    finally:
        # Limpiar temporales
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
                
    return result
