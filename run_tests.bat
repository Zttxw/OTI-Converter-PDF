@echo off
REM ══════════════════════════════════════════════════════
REM  DocuTools — Ejecutor de pruebas automatizadas
REM  Activa el entorno virtual, ejecuta pytest con reporte HTML,
REM  y retorna código de salida apropiado.
REM ══════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║         DocuTools - Suite de Pruebas            ║
echo ╚══════════════════════════════════════════════════╝
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activando entorno virtual...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activando entorno virtual (.venv)...
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] No se encontro entorno virtual (venv o .venv).
    echo        Usando Python del sistema.
)

echo.
echo [INFO] Ejecutando pruebas...
echo ────────────────────────────────────────────────────
echo.

REM Ejecutar pytest con opciones:
REM   --tb=short         : Tracebacks cortos
REM   -v                 : Modo verbose
REM   --html             : Reporte HTML (requiere pytest-html)
REM   --self-contained-html : Embeber CSS/JS en el HTML
REM   --cov              : Cobertura de código
python -m pytest tests/ --tb=short -v --html=tests/report.html --self-contained-html 2>nul
if %ERRORLEVEL% NEQ 0 (
    REM Si pytest-html no está instalado, ejecutar sin reporte HTML
    python -m pytest tests/ --tb=short -v
)

set EXIT_CODE=%ERRORLEVEL%

echo.
echo ────────────────────────────────────────────────────

if %EXIT_CODE% EQU 0 (
    echo [OK] Todas las pruebas pasaron exitosamente.
) else (
    echo [FAIL] Algunas pruebas fallaron. Codigo de salida: %EXIT_CODE%
)

if exist "tests\report.html" (
    echo [INFO] Reporte HTML generado: tests\report.html
)

echo.
exit /b %EXIT_CODE%
