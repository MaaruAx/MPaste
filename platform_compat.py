"""
platform_compat.py — MPaste
Capa de compatibilidad multiplataforma: rutas, clipboard de imágenes/GIFs,
y rutas de scripting de DaVinci Resolve.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


# ══════════════════════════════════════════════════════════════════════════════
# Directorios base
# ══════════════════════════════════════════════════════════════════════════════

def get_appdata_dir() -> Path:
    if _OS == "Windows":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif _OS == "Darwin":
        return Path.home() / "Library" / "Application Support"
    else:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def get_install_dir() -> Path:
    return get_appdata_dir() / "MMarket" / "Apps" / "MPaste"


def get_images_dir() -> Path:
    return get_install_dir() / "images"


# ══════════════════════════════════════════════════════════════════════════════
# Rutas de scripting de DaVinci Resolve
# ══════════════════════════════════════════════════════════════════════════════

def get_resolve_script_dirs() -> list[Path]:
    """
    Rutas donde se instala MPaste.lua para aparecer en
    Workspace > Scripts > Utility dentro de DaVinci Resolve.
    """
    if _OS == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        programdata = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        return [
            # Ruta personal del usuario (preferida)
            appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility",
            appdata / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Edit",
            # Ruta global del sistema
            programdata / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility",
        ]
    elif _OS == "Darwin":
        home = Path.home()
        return [
            home / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility",
            home / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Edit",
            Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"),
        ]
    else:  # Linux
        home = Path.home()
        return [
            home / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility",
            home / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Edit",
            Path("/opt/resolve/Fusion/Scripts/Utility"),
            Path("/opt/DaVinci_Resolve/Fusion/Scripts/Utility"),
        ]


def get_resolve_module_paths() -> list[Path]:
    """Rutas donde está DaVinciResolveScript.py."""
    if _OS == "Windows":
        return [
            Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"),
            Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules"),
        ]
    elif _OS == "Darwin":
        return [
            Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"),
            Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Developer" / "Scripting" / "Modules",
        ]
    else:
        return [
            Path("/opt/resolve/Developer/Scripting/Modules"),
            Path("/opt/DaVinci_Resolve/Developer/Scripting/Modules"),
            Path.home() / ".local" / "share" / "DaVinciResolve" / "Developer" / "Scripting" / "Modules",
        ]


# ══════════════════════════════════════════════════════════════════════════════
# Clipboard — imágenes y GIFs
# ══════════════════════════════════════════════════════════════════════════════

def clipboard_get_image():
    """
    Lee el portapapeles buscando una imagen o ruta de archivo (PNG/JPG/GIF/etc.).
    Devuelve (PIL.Image, str_formato) o (None, None).
    No importa PIL aquí — el llamador lo maneja para que el import sea lazy.
    """
    try:
        from PIL import Image, ImageGrab
        import io

        # 1. Intento directo: bitmap en clipboard
        try:
            img = ImageGrab.grabclipboard()
        except Exception:
            img = None

        if isinstance(img, Image.Image):
            return img, "bitmap"

        # 2. Lista de rutas de archivo (drag & drop o copy-file)
        if isinstance(img, list):
            for path in img:
                if not isinstance(path, str):
                    continue
                p = Path(path)
                if not p.is_file():
                    continue
                ext = p.suffix.lower()
                if ext in (".gif",):
                    # GIF: devolver como PIL (primer frame) — el llamador
                    # decide cómo manejarlo; la ruta real va en el formato.
                    try:
                        pil = Image.open(str(p))
                        return pil, f"gif:{p}"
                    except Exception:
                        continue
                if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
                    try:
                        return Image.open(str(p)), ext.lstrip(".")
                    except Exception:
                        continue

        # 3. Windows: SVG como texto Unicode en clipboard
        if _OS == "Windows":
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    raw = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                finally:
                    win32clipboard.CloseClipboard()
                if isinstance(raw, str) and raw.strip().startswith("<svg"):
                    try:
                        import cairosvg
                        return Image.open(io.BytesIO(
                            cairosvg.svg2png(bytestring=raw.encode("utf-8"))
                        )).convert("RGBA"), "svg-text"
                    except Exception:
                        pass
            except Exception:
                pass

        return None, None

    except Exception:
        return None, None


def clipboard_set_image(img):
    """
    Escribe una PIL.Image en el clipboard como DIB (compatible con Resolve).
    Solo Windows por ahora (Resolve corre en Windows/macOS/Linux).
    Devuelve True si tuvo éxito.
    """
    try:
        import io
        if _OS == "Windows":
            import win32clipboard
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "BMP")
            dib = buf.getvalue()[14:]
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib)
                return True
            finally:
                win32clipboard.CloseClipboard()

        elif _OS == "Darwin":
            # macOS: guardar PNG temporal y usar pbcopy con AppleScript
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            try:
                img.save(tmp, "PNG")
                result = subprocess.run(
                    ["osascript", "-e",
                     f'set the clipboard to (read (POSIX file "{tmp}") as «class PNGf»)'],
                    capture_output=True, timeout=5,
                )
                return result.returncode == 0
            finally:
                try:
                    Path(tmp).unlink()
                except Exception:
                    pass

        else:  # Linux: xclip con PNG
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            try:
                img.save(tmp, "PNG")
                for cmd in [
                    ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", tmp],
                    ["xsel", "--clipboard", "--input", tmp],
                ]:
                    try:
                        r = subprocess.run(cmd, capture_output=True, timeout=5)
                        if r.returncode == 0:
                            return True
                    except Exception:
                        continue
                return False
            finally:
                try:
                    Path(tmp).unlink()
                except Exception:
                    pass

    except Exception:
        return False
