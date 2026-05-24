import logging
from pathlib import Path
from typing import Callable, Optional
from pypdf import PdfReader, PdfWriter
from PIL import Image

logger = logging.getLogger(__name__)

def has_transparency(pil_img: Image.Image) -> bool:
    """Detecta si una imagen de Pillow tiene transparencia o canal alfa activo."""
    if pil_img.mode == 'RGBA':
        extrema = pil_img.getchannel('A').getextrema()
        return extrema[0] < 255
    if pil_img.mode == 'LA':
        extrema = pil_img.getchannel('A').getextrema()
        return extrema[0] < 255
    if pil_img.mode == 'P':
        return 'transparency' in pil_img.info
    return False

def is_almost_grayscale(pil_img: Image.Image, threshold: int = 10, fraction: float = 0.90) -> bool:
    """
    Heurística rápida utilizando el espacio de color YCbCr y su histograma.
    Determina si más del 90% (fraction) de los píxeles son casi grises (neutrales).
    """
    if pil_img.mode in ('L', '1'):
        return True
        
    total_pixels = pil_img.width * pil_img.height
    if total_pixels == 0:
        return True

    # Asegurar conversión a RGB primero para poder pasar a YCbCr sin problemas
    if pil_img.mode != 'RGB':
        try:
            pil_img_rgb = pil_img.convert('RGB')
        except Exception:
            return False
    else:
        pil_img_rgb = pil_img
        
    try:
        ycbcr = pil_img_rgb.convert('YCbCr')
        _, cb, cr = ycbcr.split()
        
        cb_hist = cb.histogram()
        cr_hist = cr.histogram()
        
        # El gris neutral en Cb y Cr tiene un valor exacto de 128.
        low_bound = max(0, 128 - threshold)
        high_bound = min(255, 128 + threshold)
        
        cb_gray = sum(cb_hist[low_bound:high_bound + 1])
        cr_gray = sum(cr_hist[low_bound:high_bound + 1])
        
        return (cb_gray / total_pixels > fraction) and (cr_gray / total_pixels > fraction)
    except Exception as e:
        logger.error(f"Error evaluando escala de grises: {e}")
        return False

def scale_image_resolution(pil_img: Image.Image, max_dpi: int) -> Image.Image:
    """
    Reduce las dimensiones de una imagen de Pillow si su resolución (DPI)
    supera el valor máximo. Estima la resolución si no se encuentra en el info.
    """
    dpi = pil_img.info.get('dpi')
    if isinstance(dpi, tuple) and len(dpi) >= 2 and dpi[0] and dpi[1]:
        dpi_val = max(dpi[0], dpi[1])
    else:
        # Heurística: asumimos un ancho físico de página estándar de 8.5 pulgadas.
        dpi_val = pil_img.width / 8.5
        
    if dpi_val > max_dpi:
        factor = max_dpi / dpi_val
        new_w = max(1, int(pil_img.width * factor))
        new_h = max(1, int(pil_img.height * factor))
        return pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return pil_img

def optimize_image(img_file, quality_level: str):
    """Aplica la compresión, redimensionamiento y conversión de escala de grises sobre una imagen."""
    try:
        pil_img = img_file.image
    except Exception as e:
        logger.warning(f"No se pudo extraer o decodificar una imagen del PDF: {e}")
        return
        
    modified = False
    
    # 1. Escala de grises (nivel "baja")
    if quality_level == "baja":
        if is_almost_grayscale(pil_img):
            try:
                pil_img = pil_img.convert("L")
                modified = True
            except Exception as e:
                logger.error(f"Error al convertir a escala de grises: {e}")
                
    # 2. Reducir resolución (DPI)
    if quality_level in ("media", "baja"):
        max_dpi = 150 if quality_level == "media" else 96
        try:
            resized = scale_image_resolution(pil_img, max_dpi)
            if resized is not pil_img:
                pil_img = resized
                modified = True
        except Exception as e:
            logger.error(f"Error al redimensionar imagen: {e}")

    # 3. Compresión/Conversión final
    if quality_level in ("media", "baja"):
        jpeg_quality = 75 if quality_level == "media" else 50
        try:
            # Si la imagen no tiene transparencia, se convierte a RGB para comprimirse como JPEG
            if not has_transparency(pil_img):
                if pil_img.mode != "RGB" and pil_img.mode != "L":
                    pil_img = pil_img.convert("RGB")
                img_file.replace(pil_img, quality=jpeg_quality)
            else:
                img_file.replace(pil_img)
        except Exception as e:
            logger.error(f"Error al reemplazar y comprimir imagen: {e}")
    elif modified:
        try:
            img_file.replace(pil_img)
        except Exception as e:
            logger.error(f"Error al reemplazar imagen modificada: {e}")

def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: str,  # "alta", "media", "baja"
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> dict:
    """
    Comprime un PDF reduciendo el tamaño manteniendo la mayor calidad posible.
    Retorna: {"original_size": int, "compressed_size": int, "reduction_percent": float, "already_optimized": bool}
    """
    # Importar FileValidator de manera segura
    from utils.file_validator import FileValidator
    
    # Validaciones obligatorias iniciales
    if quality not in ("alta", "media", "baja"):
        raise ValueError(f"Calidad de compresión inválida: {quality}")

    valid, msg = FileValidator.validate_file(input_path)
    if not valid:
        raise FileNotFoundError(msg)
        
    valid, msg = FileValidator.validate_magic_bytes(input_path, 'pdf')
    if not valid:
        raise ValueError(msg)
        
    if progress_callback:
        progress_callback(0.05, "Iniciando compresión de PDF...")

    try:
        reader = PdfReader(str(input_path))
        
        # Validar contraseña
        if reader.is_encrypted:
            raise PermissionError("El PDF está protegido con contraseña")
            
        writer = PdfWriter()
        total_pages = len(reader.pages)
        
        if total_pages == 0:
            raise ValueError("El archivo PDF no contiene páginas.")

        # Copiar páginas al writer
        for idx, page in enumerate(reader.pages):
            writer.add_page(page)
            
        # Ejecutar optimizaciones en cada página
        for idx in range(total_pages):
            page = writer.pages[idx]
            
            # Nivel "alta", "media", "baja" -> comprimir content streams
            page.compress_content_streams()
            
            # Optimización de imágenes en niveles "media" y "baja"
            if quality in ("media", "baja"):
                # Iterar sobre las imágenes de la página
                if hasattr(page, "images") and page.images:
                    for img_name in list(page.images.keys()):
                        img_file = page.images[img_name]
                        optimize_image(img_file, quality)
                        
            if progress_callback:
                # Progreso proporcional (escala entre 0.05 y 0.90)
                progress_val = 0.05 + ((idx + 1) / total_pages) * 0.85
                progress_callback(progress_val, f"Optimizando página {idx+1} de {total_pages}...")

        # Remover metadatos innecesarios
        if writer.metadata:
            for key in ["/Trapped"]:
                if key in writer.metadata:
                    del writer.metadata[key]

        # Desduplicar objetos idénticos y limpiar huérfanos
        writer.compress_identical_objects()

        if progress_callback:
            progress_callback(0.95, "Escribiendo archivo de salida...")

        # Escribir archivo final
        with open(output_path, "wb") as f:
            writer.write(f)

        original_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        
        # Si la compresión resulta en un archivo MÁS grande o igual,
        # copiamos el original sin modificaciones y marcamos already_optimized = True.
        if compressed_size >= original_size:
            logger.info("El PDF ya estaba optimizado. Manteniendo el original.")
            # Sobrescribir copiando el original
            with open(input_path, "rb") as src, open(output_path, "wb") as dst:
                dst.write(src.read())
            
            if progress_callback:
                progress_callback(1.0, "Compresión completada.")
                
            return {
                "original_size": original_size,
                "compressed_size": original_size,
                "reduction_percent": 0.0,
                "already_optimized": True
            }

        reduction_percent = ((original_size - compressed_size) / original_size) * 100.0

        if progress_callback:
            progress_callback(1.0, "Compresión finalizada con éxito.")

        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "reduction_percent": round(reduction_percent, 2),
            "already_optimized": False
        }

    except Exception as e:
        # Limpieza defensiva del archivo de salida parcial si existe
        output_path.unlink(missing_ok=True)
        logger.error(f"Error crítico en compress_pdf: {e}")
        raise e
