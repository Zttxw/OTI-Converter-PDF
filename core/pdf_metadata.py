"""
DocuTools — Módulo de lectura y escritura de metadatos PDF.

Permite leer y modificar los metadatos estándar de un PDF:
título, autor, asunto, creador y fecha de creación.

Dependencias: pypdf, utils.file_validator, utils.logger
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from pypdf import PdfReader, PdfWriter

from utils.file_validator import FileValidator

logger = logging.getLogger(__name__)

# Mapeo de claves amigables a claves internas de PDF
_METADATA_KEYS = {
    "title": "/Title",
    "author": "/Author",
    "subject": "/Subject",
    "creator": "/Creator",
    "creation_date": "/CreationDate",
}

# Claves válidas que el usuario puede establecer
_VALID_METADATA_KEYS = set(_METADATA_KEYS.keys())


def _parse_pdf_date(date_str: str) -> Optional[str]:
    """
    Convierte una fecha en formato PDF (D:YYYYMMDDHHmmSS) a formato legible.
    Retorna la fecha formateada o el string original si no se puede parsear.
    """
    if not date_str:
        return None

    try:
        # Formato típico de PDF: D:20231215103045+05'00'
        clean = date_str.replace("D:", "").strip()

        # Eliminar zona horaria si existe
        for sep in ["+", "-", "Z"]:
            if sep in clean[4:]:  # Evitar el signo negativo del año
                clean = clean[:clean.index(sep, 4)]
                break

        # Eliminar comillas
        clean = clean.replace("'", "")

        # Intentar parsear con diferentes longitudes
        formatos = [
            ("%Y%m%d%H%M%S", 14),
            ("%Y%m%d%H%M", 12),
            ("%Y%m%d", 8),
            ("%Y%m", 6),
            ("%Y", 4),
        ]

        for fmt, longitud in formatos:
            if len(clean) >= longitud:
                try:
                    fecha = datetime.strptime(clean[:longitud], fmt)
                    return fecha.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

        return date_str  # Retornar original si no se puede parsear

    except Exception:
        return date_str


def _format_date_for_pdf(date_str: str) -> str:
    """
    Convierte una fecha en formato legible a formato PDF.
    Acepta formatos: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY/MM/DD, etc.
    """
    if not date_str:
        return ""

    # Si ya tiene formato PDF, devolverla tal cual
    if date_str.startswith("D:"):
        return date_str

    formatos_entrada = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in formatos_entrada:
        try:
            fecha = datetime.strptime(date_str.strip(), fmt)
            return f"D:{fecha.strftime('%Y%m%d%H%M%S')}"
        except ValueError:
            continue

    # Si no se puede parsear, intentar devolver como formato PDF básico
    logger.warning(f"_format_date_for_pdf: no se pudo parsear fecha: '{date_str}'")
    return f"D:{date_str}"


def get_metadata(
    input_path: Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> dict:
    """
    Lee los metadatos de un archivo PDF.

    Args:
        input_path: Ruta al archivo PDF.
        progress_callback: Función opcional (percent, message) para progreso.

    Returns:
        dict con claves:
            - success (bool): Si la operación fue exitosa.
            - metadata (dict): Diccionario con los metadatos leídos:
                - title (str | None)
                - author (str | None)
                - subject (str | None)
                - creator (str | None)
                - creation_date (str | None): Fecha en formato legible.
                - producer (str | None): Herramienta que generó el PDF.
                - pages (int): Número de páginas.
                - file_size_kb (float): Tamaño del archivo en KB.
                - encrypted (bool): Si el PDF está cifrado.
            - error (str | None): Mensaje de error si falló.
    """
    resultado = {
        "success": False,
        "metadata": {},
        "error": None,
    }

    try:
        input_path = Path(input_path)

        # Validar existencia
        valid, msg = FileValidator.validate_file(input_path)
        if not valid:
            resultado["error"] = msg
            return resultado

        # Validar tamaño
        valid, msg = FileValidator.validate_size(input_path)
        if not valid:
            resultado["error"] = msg
            return resultado

        # Validar magic bytes
        valid, msg = FileValidator.validate_magic_bytes(input_path, 'pdf')
        if not valid:
            resultado["error"] = msg
            return resultado

        if progress_callback:
            progress_callback(10, "Leyendo metadatos del PDF...")

        # ── Leer PDF ────────────────────────────────────────────
        reader = PdfReader(str(input_path))

        metadata = {
            "title": None,
            "author": None,
            "subject": None,
            "creator": None,
            "creation_date": None,
            "producer": None,
            "pages": len(reader.pages),
            "file_size_kb": round(input_path.stat().st_size / 1024, 2),
            "encrypted": reader.is_encrypted,
        }

        # Si está cifrado, intentar leer lo que se pueda
        if reader.is_encrypted:
            try:
                reader.decrypt("")  # Intentar con contraseña vacía
            except Exception:
                pass

        # Extraer metadatos del documento
        if reader.metadata:
            meta = reader.metadata

            # Título
            metadata["title"] = getattr(meta, "title", None) or None

            # Autor
            metadata["author"] = getattr(meta, "author", None) or None

            # Asunto
            metadata["subject"] = getattr(meta, "subject", None) or None

            # Creador
            metadata["creator"] = getattr(meta, "creator", None) or None

            # Productor
            metadata["producer"] = getattr(meta, "producer", None) or None

            # Fecha de creación
            creation_date_raw = getattr(meta, "creation_date", None)
            if creation_date_raw:
                if isinstance(creation_date_raw, datetime):
                    metadata["creation_date"] = creation_date_raw.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    metadata["creation_date"] = _parse_pdf_date(
                        str(creation_date_raw)
                    )

            # También buscar con claves de diccionario como respaldo
            if metadata["title"] is None and "/Title" in meta:
                metadata["title"] = str(meta["/Title"]) or None

            if metadata["author"] is None and "/Author" in meta:
                metadata["author"] = str(meta["/Author"]) or None

            if metadata["subject"] is None and "/Subject" in meta:
                metadata["subject"] = str(meta["/Subject"]) or None

            if metadata["creator"] is None and "/Creator" in meta:
                metadata["creator"] = str(meta["/Creator"]) or None

        if progress_callback:
            progress_callback(100, "Metadatos leídos exitosamente")

        resultado["success"] = True
        resultado["metadata"] = metadata

        logger.info(
            f"get_metadata: '{input_path.name}' — "
            f"{metadata['pages']} páginas, {metadata['file_size_kb']} KB"
        )
        return resultado

    except Exception as e:
        resultado["error"] = f"Error inesperado al leer metadatos: {e}"
        logger.error(f"get_metadata: excepción: {e}", exc_info=True)
        return resultado


def set_metadata(
    input_path: Path,
    output_path: Path,
    metadata: dict,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> dict:
    """
    Establece o modifica los metadatos de un archivo PDF.

    Args:
        input_path: Ruta al archivo PDF de entrada.
        output_path: Ruta del archivo PDF con metadatos actualizados.
        metadata: Diccionario con los metadatos a establecer.
                  Claves válidas: 'title', 'author', 'subject', 'creator',
                  'creation_date'.
        progress_callback: Función opcional (percent, message) para progreso.

    Returns:
        dict con claves:
            - success (bool): Si la operación fue exitosa.
            - output_path (Path | None): Ruta del archivo generado.
            - metadata_set (dict): Metadatos que se establecieron.
            - error (str | None): Mensaje de error si falló.
    """
    resultado = {
        "success": False,
        "output_path": None,
        "metadata_set": {},
        "error": None,
    }

    try:
        # ── Validaciones ────────────────────────────────────────
        input_path = Path(input_path)
        output_path = Path(output_path)

        valid, msg = FileValidator.validate_pdf(input_path, check_encrypted=True)
        if not valid:
            resultado["error"] = msg
            return resultado

        if not metadata:
            resultado["error"] = "No se proporcionaron metadatos para establecer."
            return resultado

        # Validar claves de metadatos
        claves_invalidas = set(metadata.keys()) - _VALID_METADATA_KEYS
        if claves_invalidas:
            resultado["error"] = (
                f"Claves de metadatos no válidas: {', '.join(claves_invalidas)}. "
                f"Claves permitidas: {', '.join(sorted(_VALID_METADATA_KEYS))}"
            )
            return resultado

        output_path.parent.mkdir(parents=True, exist_ok=True)
        safe_output = FileValidator.get_safe_output_path(output_path)

        if progress_callback:
            progress_callback(0, "Preparando actualización de metadatos...")

        # ── Leer PDF ────────────────────────────────────────────
        if progress_callback:
            progress_callback(10, "Leyendo archivo PDF...")

        reader = PdfReader(str(input_path))
        writer = PdfWriter()

        # Copiar todas las páginas
        total_paginas = len(reader.pages)
        for page_idx in range(total_paginas):
            writer.add_page(reader.pages[page_idx])

            if progress_callback:
                porcentaje = int(((page_idx + 1) / total_paginas) * 50) + 10
                progress_callback(
                    min(porcentaje, 60),
                    f"Copiando página {page_idx + 1}/{total_paginas}",
                )

        # ── Construir diccionario de metadatos PDF ──────────────
        if progress_callback:
            progress_callback(65, "Aplicando metadatos...")

        # Primero, copiar metadatos existentes
        metadatos_pdf = {}
        if reader.metadata:
            for key, value in reader.metadata.items():
                if value is not None:
                    metadatos_pdf[key] = str(value)

        # Luego, sobrescribir con los nuevos metadatos
        metadatos_establecidos = {}

        for clave, valor in metadata.items():
            if valor is None:
                continue

            valor = str(valor).strip()
            if not valor:
                continue

            clave_pdf = _METADATA_KEYS.get(clave)
            if not clave_pdf:
                continue

            # Formatear fecha si es necesario
            if clave == "creation_date":
                valor_pdf = _format_date_for_pdf(valor)
            else:
                valor_pdf = valor

            metadatos_pdf[clave_pdf] = valor_pdf
            metadatos_establecidos[clave] = valor

        # Aplicar metadatos
        if metadatos_pdf:
            writer.add_metadata(metadatos_pdf)

        # ── Escribir resultado ──────────────────────────────────
        if progress_callback:
            progress_callback(80, "Escribiendo archivo con metadatos...")

        with open(str(safe_output), "wb") as f:
            writer.write(f)

        writer.close()

        # Verificar resultado
        if not safe_output.exists() or safe_output.stat().st_size == 0:
            resultado["error"] = "El archivo con metadatos no se creó correctamente."
            return resultado

        resultado["success"] = True
        resultado["output_path"] = safe_output
        resultado["metadata_set"] = metadatos_establecidos

        if progress_callback:
            campos = ", ".join(metadatos_establecidos.keys())
            progress_callback(
                100,
                f"Metadatos actualizados: {campos}",
            )

        logger.info(
            f"set_metadata: '{input_path.name}' — "
            f"metadatos actualizados: {', '.join(metadatos_establecidos.keys())}"
        )
        return resultado

    except PermissionError:
        resultado["error"] = (
            "No se tiene permiso para escribir el archivo de salida."
        )
        logger.error("set_metadata: PermissionError", exc_info=True)
        return resultado

    except Exception as e:
        resultado["error"] = f"Error inesperado al establecer metadatos: {e}"
        logger.error(f"set_metadata: excepción: {e}", exc_info=True)
        return resultado
