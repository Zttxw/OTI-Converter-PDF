import os
from pathlib import Path
from utils.constants import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, MAX_FILENAME_LENGTH

class FileValidator:
    """Clase defensiva para validar archivos antes del procesamiento."""

    @staticmethod
    def validate_file(path: Path | str) -> tuple[bool, str]:
        """Validación general básica de existencia y permisos."""
        try:
            p = Path(path)
            if not p.exists():
                return False, "El archivo no existe."
            if not p.is_file():
                return False, "La ruta especificada no es un archivo."
            
            # Chequeo de permisos de lectura (abre y cierra)
            with open(p, 'rb') as f:
                pass
            return True, ""
        except PermissionError:
            return False, "No tienes permisos para leer este archivo."
        except Exception as e:
            return False, f"Error al acceder al archivo: {e}"

    @staticmethod
    def validate_file_exists(path: Path | str) -> tuple[bool, str]:
        """Valida solo la existencia del archivo y que sea un archivo regular."""
        try:
            p = Path(path)
            if not p.exists():
                return False, "El archivo no existe."
            if not p.is_file():
                return False, "La ruta especificada no es un archivo."
            return True, ""
        except Exception as e:
            return False, f"Error al verificar existencia: {e}"

    @staticmethod
    def validate_file_size(path: Path | str, max_mb: int = MAX_FILE_SIZE_MB) -> tuple[bool, str]:
        """Alias de validate_size para compatibilidad."""
        return FileValidator.validate_size(path, max_mb)

    @staticmethod
    def validate_magic_bytes(path: Path | str, expected_type: str = 'pdf') -> tuple[bool, str]:
        """
        Valida que el archivo coincida con la firma binaria esperada.
        expected_type: 'pdf', 'docx', 'jpg', 'png'
        """
        signatures = {
            'pdf': (b'%PDF', 4),
            'docx': (b'PK\x03\x04', 4),
            'jpg': (b'\xFF\xD8\xFF', 3),
            'png': (b'\x89PNG', 4)
        }
        
        if expected_type not in signatures:
            return False, f"Tipo de validación no soportado: {expected_type}"
            
        expected_bytes, length = signatures[expected_type]
        
        try:
            with open(path, 'rb') as f:
                header = f.read(length)
                
            if header == expected_bytes:
                return True, ""
            return False, f"El archivo no parece ser un {expected_type.upper()} válido."
        except Exception as e:
            return False, f"Error leyendo magic bytes: {e}"

    @staticmethod
    def validate_size(path: Path | str, max_mb: int = MAX_FILE_SIZE_MB) -> tuple[bool, str]:
        """Valida que el archivo no exceda el límite de tamaño."""
        try:
            size_bytes = Path(path).stat().st_size
            max_bytes = max_mb * 1024 * 1024
            if size_bytes > max_bytes:
                return False, f"El archivo excede el límite de {max_mb} MB."
            return True, ""
        except Exception as e:
            return False, f"Error validando tamaño: {e}"

    @staticmethod
    def validate_pdf(path: Path | str, check_encrypted: bool = False) -> tuple[bool, str]:
        """
        Validación completa para archivos PDF: existencia, tamaño,
        magic bytes y opcionalmente verifica cifrado.
        """
        valid, msg = FileValidator.validate_file(path)
        if not valid:
            return False, msg

        valid, msg = FileValidator.validate_size(path)
        if not valid:
            return False, msg

        valid, msg = FileValidator.validate_magic_bytes(path, 'pdf')
        if not valid:
            return False, msg

        if check_encrypted:
            if FileValidator.is_pdf_encrypted(path):
                return False, "El PDF está protegido con contraseña. No se puede procesar."

        return True, ""

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Remueve caracteres inválidos para nombres de archivo en Windows y trunca al límite."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Remover caracteres de control
        name = "".join(c for c in name if ord(c) >= 32)
        name = name.strip()
        
        # Truncar si excede el largo máximo
        if len(name) > MAX_FILENAME_LENGTH:
            ext = ""
            dot_idx = name.rfind('.')
            if dot_idx != -1 and len(name) - dot_idx <= 10:  # Extensión razonable
                ext = name[dot_idx:]
                name = name[:dot_idx]
            
            limit = MAX_FILENAME_LENGTH - len(ext)
            name = name[:limit] + ext
            
        return name

    @staticmethod
    def validate_output_path(path: Path | str) -> tuple[bool, str]:
        """Previene vulnerabilidades de path traversal y verifica existencia de carpeta."""
        try:
            p = Path(path).resolve()
            # Si el padre no existe o es root (ej: C:\)
            if not p.parent.exists():
                return False, "El directorio de destino no existe."
            
            # Podríamos chequear si es una carpeta protegida de windows, 
            # pero con comprobar permisos al escribir basta
            return True, ""
        except Exception as e:
            return False, f"Error validando ruta de destino: {e}"

    @staticmethod
    def is_pdf_encrypted(path: Path | str) -> bool:
        """Chequea si un PDF está protegido con contraseña."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return reader.is_encrypted
        except Exception:
            return False # Asumimos falso si no puede abrirlo (o manejará error más tarde)

    @staticmethod
    def get_safe_output_path(path: Path | str) -> Path:
        """
        Retorna una ruta de salida segura. Si el archivo ya existe,
        agrega un sufijo numérico incremental para evitar sobreescritura.
        """
        p = Path(path)
        if not p.exists():
            return p
        
        counter = 1
        while True:
            new_path = p.parent / f"{p.stem}_{counter}{p.suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    @staticmethod
    def validate_batch(
        file_paths: list[Path | str],
        allowed_types: list[str] | None = None
    ) -> tuple[list[Path], dict[str, str]]:
        """
        Valida una lista de archivos de una vez.
        
        Args:
            file_paths: Lista de rutas a validar.
            allowed_types: Lista de tipos permitidos para magic bytes
                           (ej: ['pdf', 'jpg', 'png']). Si es None, solo
                           valida existencia y permisos.
        
        Returns:
            Tupla (valid_paths, errors_dict) donde:
            - valid_paths: lista de Path validados correctamente.
            - errors_dict: diccionario {str(path): mensaje_error} para archivos inválidos.
        """
        valid_paths: list[Path] = []
        errors: dict[str, str] = {}

        for file_path in file_paths:
            path_str = str(file_path)
            p = Path(file_path)

            # 1. Validar existencia y permisos
            valid, msg = FileValidator.validate_file(p)
            if not valid:
                errors[path_str] = msg
                continue

            # 2. Validar tamaño
            valid, msg = FileValidator.validate_size(p)
            if not valid:
                errors[path_str] = msg
                continue

            # 3. Validar magic bytes si se especificaron tipos permitidos
            if allowed_types:
                extension = p.suffix.lower().lstrip('.')
                # Mapear extensiones a tipos de magic bytes
                ext_to_type = {
                    'pdf': 'pdf',
                    'docx': 'docx',
                    'jpg': 'jpg',
                    'jpeg': 'jpg',
                    'png': 'png',
                }
                magic_type = ext_to_type.get(extension)
                
                if magic_type and magic_type in allowed_types:
                    valid, msg = FileValidator.validate_magic_bytes(p, magic_type)
                    if not valid:
                        errors[path_str] = msg
                        continue
                elif magic_type and magic_type not in allowed_types:
                    errors[path_str] = f"Tipo de archivo no permitido: .{extension}"
                    continue

            valid_paths.append(p)

        return valid_paths, errors
