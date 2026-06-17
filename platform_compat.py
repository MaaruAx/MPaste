"""
platform_compat.py — MPaste
Cross-platform layer: paths, image/GIF clipboard, DaVinci Resolve scripting paths.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


# ── Base directories ──────────────────────────────────────────────────────────

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


# ── DaVinci Resolve script paths ──────────────────────────────────────────────

def get_resolve_script_dirs() -> list[Path]:
    """
    Paths where MPaste.lua is installed so it appears under
    Workspace > Scripts > Utility inside DaVinci Resolve.
    """
    if _OS == "Windows":
        appdata      = Path(os.environ.get("APPDATA", ""))
        programdata  = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        return [
            appdata     / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility",
            appdata     / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Edit",
            programdata / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility",
        ]
    elif _OS == "Darwin":
        home = Path.home()
        return [
            home / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility",
            home / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Edit",
            Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"),
        ]
    else:
        home = Path.home()
        return [
            home / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility",
            home / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Edit",
            Path("/opt/resolve/Fusion/Scripts/Utility"),
            Path("/opt/DaVinci_Resolve/Fusion/Scripts/Utility"),
        ]


def get_resolve_module_paths() -> list[Path]:
    """Paths where DaVinciResolveScript.py lives."""
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


# ── Clipboard — read ──────────────────────────────────────────────────────────

def clipboard_get_image():
    """
    Read image/GIF from the clipboard.
    Returns (PIL.Image, fmt_str) or (None, None).

    Windows priority order:
      1. CF_DIB  — bitmap copied directly (screenshot, Photoshop, etc.)
      2. CF_HDROP — file path(s) copied from Explorer; supports PNG/JPG/GIF/etc.
      3. CF_UNICODETEXT — SVG text (requires cairosvg, optional)

    macOS / Linux: falls back to PIL.ImageGrab.grabclipboard().
    """
    from PIL import Image
    import io

    if _OS == "Windows":
        try:
            import win32clipboard
            import win32con
            win32clipboard.OpenClipboard()
            try:
                # ── 1. DIB (device-independent bitmap) ───────────────────────
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                    # DIB data starts with BITMAPINFOHEADER — reconstruct BMP
                    bmp_header = b'BM' + (len(data) + 14).to_bytes(4, 'little') \
                                 + b'\x00\x00\x00\x00' + b'\x36\x00\x00\x00'
                    bmp_data = bmp_header + data
                    img = Image.open(io.BytesIO(bmp_data)).convert("RGB")
                    return img, "bitmap"

                # ── 2. File drop (Explorer copy) ─────────────────────────────
                CF_HDROP = 15
                if win32clipboard.IsClipboardFormatAvailable(CF_HDROP):
                    paths = win32clipboard.GetClipboardData(CF_HDROP)
                    for p_str in paths:
                        p = Path(p_str)
                        if not p.is_file():
                            continue
                        ext = p.suffix.lower()
                        if ext == ".gif":
                            img = Image.open(str(p))
                            return img, f"gif:{p}"
                        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
                            return Image.open(str(p)).convert("RGBA"), ext.lstrip(".")

                # ── 3. SVG as unicode text ────────────────────────────────────
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    raw = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    if isinstance(raw, str) and raw.strip().startswith("<svg"):
                        try:
                            import cairosvg
                            png = cairosvg.svg2png(bytestring=raw.encode("utf-8"))
                            return Image.open(io.BytesIO(png)).convert("RGBA"), "svg-text"
                        except Exception:
                            pass

            finally:
                win32clipboard.CloseClipboard()

        except Exception as e:
            print(f"[clipboard_get_image] win32 error: {e}")

        return None, None

    else:
        # macOS / Linux
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                return img, "bitmap"
            if isinstance(img, list):
                for p_str in img:
                    p = Path(str(p_str))
                    if not p.is_file():
                        continue
                    ext = p.suffix.lower()
                    if ext == ".gif":
                        return Image.open(str(p)), f"gif:{p}"
                    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
                        return Image.open(str(p)).convert("RGBA"), ext.lstrip(".")
        except Exception as e:
            print(f"[clipboard_get_image] error: {e}")

        return None, None


# ── Clipboard — write ─────────────────────────────────────────────────────────

def clipboard_set_image(img) -> bool:
    """
    Write a PIL.Image to the clipboard as DIB (DaVinci Resolve compatible).
    Returns True on success.
    """
    import io

    if _OS == "Windows":
        try:
            import win32clipboard
            import win32con
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "BMP")
            # Strip the 14-byte BMP file header — CF_DIB needs raw BITMAPINFOHEADER+data
            dib = buf.getvalue()[14:]
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, dib)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"[clipboard_set_image] error: {e}")
            return False

    elif _OS == "Darwin":
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        try:
            img.save(tmp, "PNG")
            r = subprocess.run(
                ["osascript", "-e",
                 f'set the clipboard to (read (POSIX file "{tmp}") as «class PNGf»)'],
                capture_output=True, timeout=5,
            )
            return r.returncode == 0
        finally:
            try: Path(tmp).unlink()
            except Exception: pass

    else:  # Linux
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        try:
            img.save(tmp, "PNG")
            for cmd in [
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", tmp],
                ["xsel",  "--clipboard", "--input", tmp],
            ]:
                try:
                    r = subprocess.run(cmd, capture_output=True, timeout=5)
                    if r.returncode == 0:
                        return True
                except Exception:
                    continue
            return False
        finally:
            try: Path(tmp).unlink()
            except Exception: pass
