@echo off
chcp 437 >nul
:: ══════════════════════════════════════════════════════════════════════
::  MPaste — Windows build optimizado para tamaño reducido
::  Migrado de pywebview → PySide6 + QWebEngine (igual que MCopy)
::
::  Exclusiones:
::  [A] tkinter/_tkinter  → elimina tcl_data/ y tk_data/ (~20 MB)
::  [B] stdlib inutilizado → email, xml, http, tests, etc. (~15 MB)
::  [C] zoneinfo/tzdata   → base de datos UTC completa (~5 MB)
::  [D] Qt módulos no usados → Qt3D, Bluetooth, Charts, etc. (~30 MB)
::  Post-build: borra Qt translations, sqldrivers y plugins sin uso (~10 MB)
::
::  platform_compat.py NO se pasa con --add-data: PyInstaller lo detecta
::  como módulo importado. Agregarlo como dato lo duplicaría.
:: ══════════════════════════════════════════════════════════════════════

set "ICON_PATH=C:\Users\maaru\Downloads\MPaste.ico"

echo.
echo [1/5] Instalando dependencias...
pip install PySide6 Pillow pywin32 --quiet
if errorlevel 1 ( echo ERROR: Fallo al instalar dependencias & pause & exit /b 1 )

echo [2/5] Compilando MPaste...
pyinstaller ^
  --noconsole ^
  --onedir ^
  --name MPaste ^
  --upx-dir "C:\Users\maaru\Downloads\upx-5.2.0-win64\upx-5.2.0-win64" ^
  --upx-exclude vcruntime140.dll ^
  --upx-exclude python3*.dll ^
  --upx-exclude QtWebEngineCore.dll ^
  --icon="%ICON_PATH%" ^
  --add-data "ui.html;." ^
  --add-data "settings.html;." ^
  --add-data "fonts;fonts" ^
  --add-data "MPaste.lua;." ^
  --add-data "install.py;." ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtWidgets ^
  --hidden-import PySide6.QtWebEngineCore ^
  --hidden-import PySide6.QtWebEngineWidgets ^
  --hidden-import PySide6.QtWebChannel ^
  --hidden-import PySide6.QtNetwork ^
  --hidden-import PySide6.QtOpenGL ^
  --hidden-import PySide6.QtOpenGLWidgets ^
  --hidden-import PySide6.QtPrintSupport ^
  --hidden-import win32clipboard ^
  --hidden-import win32api ^
  --hidden-import win32con ^
  --hidden-import PIL ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageGrab ^
  --exclude-module pywebview ^
  --exclude-module tkinter ^
  --exclude-module _tkinter ^
  --exclude-module zoneinfo ^
  --exclude-module tzdata ^
  --exclude-module email ^
  --exclude-module html ^
  --exclude-module http ^
  --exclude-module urllib ^
  --exclude-module xml ^
  --exclude-module xmlrpc ^
  --exclude-module unittest ^
  --exclude-module doctest ^
  --exclude-module pdb ^
  --exclude-module difflib ^
  --exclude-module calendar ^
  --exclude-module ftplib ^
  --exclude-module imaplib ^
  --exclude-module smtplib ^
  --exclude-module poplib ^
  --exclude-module nntplib ^
  --exclude-module telnetlib ^
  --exclude-module shelve ^
  --exclude-module dbm ^
  --exclude-module zipapp ^
  --exclude-module turtle ^
  --exclude-module turtledemo ^
  --exclude-module webbrowser ^
  --exclude-module lib2to3 ^
  --exclude-module PySide6.Qt3DAnimation ^
  --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.Qt3DExtras ^
  --exclude-module PySide6.Qt3DInput ^
  --exclude-module PySide6.Qt3DLogic ^
  --exclude-module PySide6.Qt3DRender ^
  --exclude-module PySide6.QtBluetooth ^
  --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtDataVisualization ^
  --exclude-module PySide6.QtDesigner ^
  --exclude-module PySide6.QtHelp ^
  --exclude-module PySide6.QtLocation ^
  --exclude-module PySide6.QtMultimedia ^
  --exclude-module PySide6.QtMultimediaWidgets ^
  --exclude-module PySide6.QtNfc ^
  --exclude-module PySide6.QtPositioning ^
  --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtQuick3D ^
  --exclude-module PySide6.QtQuickControls2 ^
  --exclude-module PySide6.QtQuickWidgets ^
  --exclude-module PySide6.QtRemoteObjects ^
  --exclude-module PySide6.QtScxml ^
  --exclude-module PySide6.QtSensors ^
  --exclude-module PySide6.QtSerialBus ^
  --exclude-module PySide6.QtSerialPort ^
  --exclude-module PySide6.QtSql ^
  --exclude-module PySide6.QtStateMachine ^
  --exclude-module PySide6.QtSvg ^
  --exclude-module PySide6.QtSvgWidgets ^
  --exclude-module PySide6.QtTest ^
  --exclude-module PySide6.QtTextToSpeech ^
  --exclude-module PySide6.QtUiTools ^
  --exclude-module PySide6.QtVirtualKeyboard ^
  --exclude-module PySide6.QtWebSockets ^
  --exclude-module PySide6.QtXml ^
  main.py

if errorlevel 1 ( echo ERROR: Fallo al compilar & pause & exit /b 1 )

echo [3/5] Eliminando archivos Qt innecesarios...
rd /s /q "dist\MPaste\_internal\PySide6\Qt\translations" 2>nul
rd /s /q "dist\MPaste\_internal\PySide6\Qt\plugins\sqldrivers"  2>nul
rd /s /q "dist\MPaste\_internal\PySide6\Qt\plugins\geoservices"  2>nul
rd /s /q "dist\MPaste\_internal\PySide6\Qt\plugins\position"  2>nul
rd /s /q "dist\MPaste\_internal\PySide6\Qt\plugins\sensors"  2>nul
rd /s /q "dist\MPaste\_internal\PySide6\Qt\plugins\canbus"  2>nul
rd /s /q "dist\MPaste\_internal\PySide6\Qt\plugins\serialport"  2>nul

echo [4/5] Limpiando artefactos de build...
rmdir /s /q build 2>nul
del MPaste.spec 2>nul

echo [5/5] Resultado:
for /f "tokens=3" %%a in ('dir /s /-c "dist\MPaste" ^| find "archivos"') do set FCOUNT=%%a
echo  Archivos en dist\MPaste: %FCOUNT%

echo.
echo ================================================================
echo  Listo: dist\MPaste\MPaste.exe
echo  Empaqueta con MPaste.iss usando Inno Setup
echo.
echo  NOTA: shiboken6 es inamovible (capa de binding de PySide6).
echo  Los archivos de Chromium (icudtl.dat, .pak) son el motor de
echo  QWebEngine: inamovibles. Con lzma2/ultra64 el instalador
echo  deberia quedar en 80-110 MB.
echo ================================================================
pause
