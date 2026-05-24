# OTI - Converter 🚀

**OTI - Converter** es una suite de utilidades de escritorio desarrollada en Python orientada a la optimización, conversión y gestión de archivos PDF y documentos ofimáticos. Diseñada específicamente para facilitar los flujos de trabajo documentales (como en municipalidades u oficinas de atención).

## ✨ Características Principales

*   **PDF a Word:** Conversión precisa de documentos PDF a formato editable `.docx`.
*   **Comprimir PDF:** Motor de compresión inteligente que reduce el tamaño de los documentos pesados limpiando objetos huérfanos y reduciendo los DPI, ideal para envíos por correo o subidas a plataformas estatales.
*   **Word / Excel / PowerPoint a PDF:** Conversión bidireccional nativa a PDF.
*   **PDF a Imágenes:** Extrae páginas completas en formato `.jpg` o `.png`.
*   **Imágenes a PDF:** Compila recibos, fotos o escaneos en un único documento PDF.
*   **Fusión y División de PDF:** Une varios documentos o extrae páginas específicas.
*   **Seguridad:** Quita contraseñas de PDFs (si tienes la original).

## 🛠️ Tecnologías Usadas

*   **Lenguaje:** Python 3.13
*   **Interfaz Gráfica (UI):** CustomTkinter (diseño moderno y oscuro).
*   **Motores de Procesamiento:** `PyMuPDF (fitz)`, `pypdf`, `pdf2docx`, `docx2pdf`, `Pillow`.
*   **Empaquetado:** PyInstaller y compilador Inno Setup para generar el ejecutable de Windows.

## 💻 Instalación (Para Desarrollo)

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/oti-converter.git
   cd oti-converter
   ```
2. Crea un entorno virtual y actívalo:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicia la aplicación:
   ```bash
   python main.py
   ```

## 📦 Compilación (Para Producción)

Si deseas empaquetar el proyecto para que corra en computadoras sin Python instalado:
1. Ejecuta el archivo `build.bat`. Esto creará los binarios usando PyInstaller y los pondrá en la carpeta `dist/OTI-Converter`.
2. Ejecuta el archivo de Inno Setup `installer.iss` usando `ISCC.exe` o el programa gráfico de Inno Setup. 
3. El instalador final `.exe` se guardará en la carpeta `Output/`.

## 🤝 Contribución

Cualquier mejora, corrección de errores (bugs) o sugerencia de nuevas herramientas es bienvenida. Simplemente abre un *Issue* o envía un *Pull Request*.

## 📜 Licencia

Desarrollado para facilitar las labores administrativas y de tecnología de la información.
