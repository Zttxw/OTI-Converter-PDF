@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ════════════════════════════════════════════════════════════
echo  OTI - Converter — Configuracion de Entorno de Desarrollo
echo ════════════════════════════════════════════════════════════
echo.

echo Comprobando instalacion de Python...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    pause
    exit /b 1
)

echo Creando entorno virtual (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al crear el entorno virtual.
    pause
    exit /b 1
)

echo Activando entorno virtual...
call venv\Scripts\activate.bat

echo Actualizando pip...
python -m pip install --upgrade pip

echo Instalando dependencias de requirements.txt...
pip install -r requirements.txt

echo.
echo ════════════════════════════════════════════════════════════
echo [OK] Entorno configurado correctamente.
echo Para iniciar, asegurate de tener la carpeta 'poppler' configurada
echo si vas a usar la conversion de PDF a Imagen.
echo ════════════════════════════════════════════════════════════
pause
