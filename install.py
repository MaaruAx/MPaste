"""
install.py — MPaste
Instalador/configurador cross-platform.

Qué hace:
  1. Instala dependencias Python (pip).
  2. Crea carpetas de datos en el directorio apropiado del SO.
  3. Escribe MPaste.lua en la carpeta de Scripts de DaVinci Resolve
     para que aparezca en Workspace > Scripts > Utility.
  4. En Windows: crea acceso directo en el escritorio (opcional).

Uso:
  python install.py           # instalación normal
  python install.py --uninstall  # elimina el script Lua y los accesos directos
"""

import sys
import os
import platform
import subprocess
import argparse
import shutil
from pathlib import Path

_OS = platform.system()

# ── Importar rutas desde platform_compat ────────────────────────────────────
# Asegurarse de que platform_compat esté junto a install.py
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from platform_compat import (
    get_install_dir,
    get_images_dir,
    get_resolve_script_dirs,
)

INSTALL_DIR = get_install_dir()
IMAGES_DIR  = get_images_dir()

# ══════════════════════════════════════════════════════════════════════════════
# Dependencias
# ══════════════════════════════════════════════════════════════════════════════

_DEPS_ALL = [
    "PySide6",
    "Pillow",
    "pywin32; sys_platform == 'win32'",
]

_DEPS_OPTIONAL = [
    "cairosvg",   # SVG→PNG en clipboard
]


def _pip(*args):
    return subprocess.run(
        [sys.executable, "-m", "pip", *args,
         "--quiet", "--disable-pip-version-check", "--no-warn-script-location"],
        capture_output=True, text=True,
    )


def install_deps(verbose: bool = True):
    print("\n── Instalando dependencias ──────────────────────────────────────")
    failed = []
    for pkg in _DEPS_ALL:
        name = pkg.split(";")[0].strip()
        print(f"  {name}...", end=" ", flush=True)
        r = _pip("install", pkg)
        if r.returncode == 0:
            print("OK")
        else:
            print("ERROR")
            failed.append((name, r.stderr.strip()))

    for pkg in _DEPS_OPTIONAL:
        print(f"  {pkg} (opcional)...", end=" ", flush=True)
        r = _pip("install", pkg)
        print("OK" if r.returncode == 0 else "omitido")

    if failed:
        print("\n⚠  Algunas dependencias fallaron:")
        for name, err in failed:
            print(f"   - {name}: {err or 'sin detalle'}")
        print("\n   Solución manual:")
        print(f"     {sys.executable} -m pip install PySide6 Pillow pywin32\n")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Lua launcher
# ══════════════════════════════════════════════════════════════════════════════

_LUA_TEMPLATE = """\
-- MPaste launcher para DaVinci Resolve
-- Generado automáticamente por install.py (MMarket)
-- Aparece en: Workspace > Scripts > Utility > MPaste
local function launch()
    local cmd = {LAUNCH_CMD}
    os.execute(cmd)
end
launch()
"""


def _build_launch_cmd() -> str:
    """
    Devuelve la línea de comando (como string Lua) para lanzar MPaste.
    Prioridad: exe empaquetado → pythonw (Win) → python.
    """
    # ¿Hay un exe compilado junto a install.py?
    exe_candidates = [
        _HERE / "MPaste.exe",
        _HERE / "MPaste",
        _HERE / "dist" / "MPaste" / "MPaste.exe",
        _HERE / "dist" / "MPaste" / "MPaste",
    ]
    for candidate in exe_candidates:
        if candidate.is_file():
            escaped = str(candidate).replace("\\", "\\\\")
            return f'\'"{escaped}"\''

    # No hay exe: usar Python
    main_py = _HERE / "main.py"
    if not main_py.is_file():
        # Instalado en INSTALL_DIR
        main_py = INSTALL_DIR / "main.py"

    if _OS == "Windows":
        # pythonw.exe para no mostrar consola
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        interp  = str(pythonw) if pythonw.is_file() else sys.executable
    else:
        interp = sys.executable

    interp_esc   = str(interp).replace("\\", "\\\\")
    main_py_esc  = str(main_py).replace("\\", "\\\\")
    return f'\'"{interp_esc}" "{main_py_esc}"\''


def install_lua():
    print("\n── Instalando script Lua en DaVinci Resolve ─────────────────────")
    lua_content = _LUA_TEMPLATE.replace("{LAUNCH_CMD}", _build_launch_cmd())
    installed   = False

    for scripts_dir in get_resolve_script_dirs():
        try:
            scripts_dir.mkdir(parents=True, exist_ok=True)
            lua_path = scripts_dir / "MPaste.lua"
            lua_path.write_text(lua_content, encoding="utf-8")
            print(f"  ✓ {lua_path}")
            installed = True
            break  # basta con la primera que funcione
        except PermissionError:
            print(f"  ✗ Sin permiso: {scripts_dir}")
        except Exception as e:
            print(f"  ✗ {scripts_dir}: {e}")

    if not installed:
        print("  ⚠  No se pudo instalar el script Lua.")
        print("     Puedes copiarlo manualmente a una de estas rutas:")
        for d in get_resolve_script_dirs():
            print(f"       {d}")
    return installed


def uninstall_lua():
    print("\n── Eliminando script Lua ────────────────────────────────────────")
    for scripts_dir in get_resolve_script_dirs():
        lua_path = scripts_dir / "MPaste.lua"
        if lua_path.is_file():
            try:
                lua_path.unlink()
                print(f"  ✓ Eliminado: {lua_path}")
            except Exception as e:
                print(f"  ✗ {lua_path}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Carpetas de datos
# ══════════════════════════════════════════════════════════════════════════════

def create_data_dirs():
    print("\n── Creando carpetas de datos ────────────────────────────────────")
    for d in (INSTALL_DIR, IMAGES_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ {d}")
        except Exception as e:
            print(f"  ✗ {d}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Acceso directo en escritorio (Windows)
# ══════════════════════════════════════════════════════════════════════════════

def create_shortcut_windows():
    if _OS != "Windows":
        return
    try:
        import winshell  # type: ignore
        from win32com.client import Dispatch  # type: ignore

        desktop    = Path(winshell.desktop())
        lnk_path   = desktop / "MPaste.lnk"
        exe_path   = _HERE / "MPaste.exe"
        target     = str(exe_path) if exe_path.is_file() else sys.executable
        wkg_dir    = str(_HERE)
        icon       = str(exe_path) if exe_path.is_file() else ""

        shell = Dispatch("WScript.Shell")
        sc    = shell.CreateShortCut(str(lnk_path))
        sc.Targetpath        = target
        sc.WorkingDirectory  = wkg_dir
        sc.IconLocation      = icon
        sc.Description       = "MPaste — MMarket for DaVinci Resolve"
        sc.save()
        print(f"\n── Acceso directo creado: {lnk_path}")
    except ImportError:
        print("\n  (winshell no disponible, acceso directo omitido)")
    except Exception as e:
        print(f"\n  ✗ Error creando acceso directo: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Copiar assets a INSTALL_DIR (para dev sin exe)
# ══════════════════════════════════════════════════════════════════════════════

def copy_assets():
    print("\n── Copiando archivos de la app ──────────────────────────────────")
    for fname in ("main.py", "ui.html", "platform_compat.py"):
        src = _HERE / fname
        dst = INSTALL_DIR / fname
        if src.is_file():
            try:
                shutil.copy2(src, dst)
                print(f"  ✓ {fname}")
            except Exception as e:
                print(f"  ✗ {fname}: {e}")

    for folder in ("fonts",):
        src = _HERE / folder
        dst = INSTALL_DIR / folder
        if src.is_dir():
            try:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  ✓ {folder}/")
            except Exception as e:
                print(f"  ✗ {folder}/: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Punto de entrada
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="MPaste installer")
    parser.add_argument("--uninstall",   action="store_true", help="Eliminar script Lua y accesos directos")
    parser.add_argument("--no-deps",     action="store_true", help="Omitir instalación de dependencias")
    parser.add_argument("--no-shortcut", action="store_true", help="Omitir acceso directo en escritorio")
    args = parser.parse_args()

    print("╔══════════════════════════════════════╗")
    print("║  MPaste — Installer  (MMarket)       ║")
    print(f"║  SO: {_OS:<32}║")
    print("╚══════════════════════════════════════╝")

    if args.uninstall:
        uninstall_lua()
        print("\nDesinstalación completada.")
        return

    create_data_dirs()

    if not args.no_deps:
        install_deps()

    copy_assets()
    install_lua()

    if not args.no_shortcut:
        create_shortcut_windows()

    print("\n══════════════════════════════════════════")
    print("  MPaste instalado correctamente.")
    print(f"  Datos en: {INSTALL_DIR}")
    print("  Abre DaVinci Resolve y ve a:")
    print("    Workspace > Scripts > Utility > MPaste")
    print("══════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
