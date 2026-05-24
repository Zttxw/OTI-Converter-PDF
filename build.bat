@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ════════════════════════════════════════════════════════════
echo  OTI - Converter — Construcción de Ejecutable (PyInstaller)
echo  Modo: --onedir (carpeta portable)
echo ════════════════════════════════════════════════════════════
echo.

REM 1. Verificar UPX
upx --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] UPX no esta instalado o no esta en el PATH.
    echo               El ejecutable final podria ser mas grande de lo esperado.
) else (
    echo [OK] UPX detectado.
)

REM 2. Limpiar build y dist
echo.
echo Limpiando carpetas de compilacion previas...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo [OK] Carpetas limpiadas.

REM 3. Activar venv
echo.
echo Activando entorno virtual...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Entorno virtual activado.
) else (
    echo [ERROR] No se encontro venv\Scripts\activate.bat
    echo         Ejecuta setup_env.bat primero.
    pause
    exit /b 1
)

REM 4. Actualizar pyinstaller
echo.
echo Asegurando dependencias...
pip install --upgrade pyinstaller > nul 2>&1
echo [OK] PyInstaller actualizado.

REM 5. Compilar con el spec correcto
echo.
echo Compilando ejecutable con PyInstaller (--onedir)...
echo.
pyinstaller docutools.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ════════════════════════════════════════════════════════════
    echo  [ERROR] Fallo la compilacion. Revisa los logs arriba.
    echo ════════════════════════════════════════════════════════════
    pause
    exit /b 1
)

REM 6. Verificar que el ejecutable se creó
set EXE_PATH=dist\OTI-Converter\OTI-Converter.exe
if not exist "%EXE_PATH%" (
    echo [ERROR] No se encontro el ejecutable en %EXE_PATH%
    pause
    exit /b 1
)

REM 7. Verificar poppler y copiar si no esta embebido
echo.
if not exist "dist\OTI-Converter\poppler\bin" (
    if exist "poppler\bin" (
        echo Copiando Poppler al directorio dist (fallback)...
        mkdir "dist\OTI-Converter\poppler\bin" 2>nul
        xcopy /s /e /y "poppler\bin" "dist\OTI-Converter\poppler\bin" >nul
        echo [OK] Poppler copiado.
    )
)

REM 8. Mostrar tamaño de la carpeta
echo.
echo [OK] Compilacion exitosa.
echo Ejecutable: %EXE_PATH%
for %%I in ("%EXE_PATH%") do set size=%%~zI
set /a sizeMB=%size%/1024/1024
echo Tamano del ejecutable: ~%sizeMB% MB

REM 9. Ejecutar para validacion
echo.
echo Iniciando OTI-Converter.exe para validacion...
start "" "%EXE_PATH%"

echo.
echo ════════════════════════════════════════════════════════════
echo  CHECKLIST DE VALIDACION:
echo  [ ] Arranca en menos de 3 segundos?
echo  [ ] Funciona sin Python instalado? (Probar en otra PC)
echo  [ ] Funciona en rutas con espacios y tildes?
echo  [ ] PDF a Word funciona?
echo  [ ] PDF a Imagen funciona?
echo  [ ] La carpeta de destino persiste entre herramientas?
echo  [ ] La carpeta de destino persiste al cerrar y reabrir?
echo  [ ] Log se crea en %%APPDATA%%\OTI-Converter\logs\?
echo  [ ] Windows Defender no lo bloquea?
echo ════════════════════════════════════════════════════════════
echo.
pause
