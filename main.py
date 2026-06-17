"""
main.py — MPaste
Herramienta de imágenes/GIFs para DaVinci Resolve.
MMarket Ecosystem

Cambios vs versión anterior:
  - PySide6 + QWebEngineWidgets (eliminado pywebview)
  - QWebChannel para API JS↔Python
  - Guard de instancia única con QLocalServer (enfoca ventana existente)
  - GIF: inserción en Resolve via scripting (ruta local → ImportMedia)
  - platform_compat.py para rutas y clipboard cross-platform
  - Cero dependencias en runtime (todo declarado en install.py / build.bat)
"""

import sys
import os

# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 0 — freeze_support (must come before any heavy imports)
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

_IS_FROZEN  = getattr(sys, "frozen", False)
_BUNDLE_DIR = getattr(sys, "_MEIPASS", None)

if _IS_FROZEN:
    _SCRIPT_DIR = os.path.dirname(sys.executable)
    _BUNDLE_DIR = _BUNDLE_DIR or _SCRIPT_DIR
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE_DIR = _SCRIPT_DIR

# platform_compat debe estar junto a main.py o en _BUNDLE_DIR
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import json
import threading
import glob
import tempfile
import datetime
import time
import io
import platform
from pathlib import Path

from platform_compat import (
    get_install_dir,
    get_images_dir,
    get_resolve_module_paths,
    clipboard_get_image,
    clipboard_set_image,
)

_OS = platform.system()

# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 1 — Paths
# ══════════════════════════════════════════════════════════════════════════════
INSTALL_DIR   = get_install_dir()
IMAGES_DIR    = get_images_dir()
SETTINGS_FILE = INSTALL_DIR / "settings.json"

_UI_BUNDLE = Path(_BUNDLE_DIR) / "ui.html"
_UI_SCRIPT = Path(_SCRIPT_DIR) / "ui.html"
_UI_INSTALL = INSTALL_DIR / "ui.html"

for _d in (INSTALL_DIR, IMAGES_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# Resolve ui.html and settings.html — dev always uses script dir first
if _IS_FROZEN:
    UI_FILE       = _UI_BUNDLE if _UI_BUNDLE.is_file() else _UI_INSTALL
    SETTINGS_HTML = Path(_BUNDLE_DIR) / "settings.html"
    if not SETTINGS_HTML.is_file():
        SETTINGS_HTML = INSTALL_DIR / "settings.html"
else:
    UI_FILE       = _UI_SCRIPT if _UI_SCRIPT.is_file() else _UI_INSTALL
    SETTINGS_HTML = Path(_SCRIPT_DIR) / "settings.html"
    if not SETTINGS_HTML.is_file():
        SETTINGS_HTML = INSTALL_DIR / "settings.html"

# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 2 — Resolve modules in sys.path
# ══════════════════════════════════════════════════════════════════════════════
for _rp in get_resolve_module_paths():
    _rp = str(_rp)
    if os.path.isdir(_rp) and _rp not in sys.path:
        sys.path.insert(0, _rp)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 3 — Settings
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULT_SETTINGS = {
    "accent":        "#f5c842",
    "theme":         "mmarket",
    "font":          "barlow",
    "lang":          "es",
    "always_on_top": True,
}

_VALID_THEMES = {"mmarket", "rosepine", "gruvbox"}

# tx3 (subtle text) color per theme — used by the resize grip
_THEME_TX3 = {
    "mmarket":  "#555555",
    "rosepine": "#6e6a86",
    "gruvbox":  "#928374",
}
_VALID_FONTS  = {"barlow", "monaspace"}
_VALID_LANGS  = {"es", "en", "hi", "hg"}


def _load_settings() -> dict:
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        out = dict(_DEFAULT_SETTINGS)
        for k, v in data.items():
            if k in _DEFAULT_SETTINGS:
                out[k] = v
        return out
    except Exception:
        return dict(_DEFAULT_SETTINGS)


def _save_settings(data: dict) -> bool:
    try:
        import re
        accent = str(data.get("accent", "#f5c842"))[:20].strip()
        if not re.match(r'^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$', accent):
            accent = "#f5c842"
        theme = str(data.get("theme", "dark"))
        if theme not in _VALID_THEMES:
            theme = "dark"
        lang = str(data.get("lang", "es"))
        if lang not in _VALID_LANGS:
            lang = "es"
        font = str(data.get("font", "barlow"))
        if font not in _VALID_FONTS:
            font = "barlow"
        safe = {
            "accent":        accent,
            "theme":         theme,
            "font":          font,
            "lang":          lang,
            "always_on_top": bool(data.get("always_on_top", True)),
        }
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(safe, f, indent=2)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 4 — Resolve helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get_resolve():
    try:
        import DaVinciResolveScript as dvr
    except ImportError:
        raise RuntimeError(
            "DaVinciResolveScript no encontrado.\n"
            "MPaste requiere DaVinci Resolve Studio."
        )
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        raise RuntimeError(
            "DaVinci Resolve no responde.\n"
            "Asegúrate de que esté abierto con un proyecto activo."
        )
    pm   = resolve.GetProjectManager()
    proj = pm.GetCurrentProject() if pm else None
    if not proj:
        raise RuntimeError("No hay proyecto abierto en Resolve.")
    return resolve, proj, proj.GetCurrentTimeline()


def _tc_to_frames(tc_str: str, fps: float) -> int:
    try:
        tc = str(tc_str).strip().replace(";", ":")
        h, m, s, f = [int(x) for x in tc.split(":")]
        return int(round((h * 3600 + m * 60 + s) * fps)) + f
    except Exception:
        return 0


def _find_free_video_track(tl, at_frame: int) -> int:
    """
    Return the first video track index with no clip occupying at_frame.
    Creates a new video track if all existing tracks are occupied.
    """
    try:
        n = tl.GetTrackCount("video")
    except Exception:
        return 1
    for idx in range(1, n + 1):
        try:
            items = tl.GetItemListInTrack("video", idx) or []
            occupied = any(
                item.GetStart() <= at_frame < item.GetEnd()
                for item in items
            )
            if not occupied:
                return idx
        except Exception:
            return idx
    # All tracks occupied — create a new video track
    try:
        tl.AddTrack("video")
        return n + 1
    except Exception:
        return 1


def _insert_at_frame(mp, clip, record_frame: int, track_idx: int) -> bool:
    """Insert clip at record_frame on track_idx using AppendToTimeline clipInfo."""
    try:
        result = mp.AppendToTimeline([{
            "mediaPoolItem": clip,
            "mediaType":     1,          # video only
            "trackIndex":    track_idx,
            "recordFrame":   record_frame,
        }])
        return bool(result)
    except Exception as e:
        print(f"[_insert_at_frame] {e}")
        return False


def _append_clip(mp, clip) -> bool:
    """Intenta agregar clip a la timeline con varios métodos de fallback."""
    for payload in [
        [clip],
        [{"mediaPoolItem": clip, "mediaType": 1}],
        [{"mediaPoolItem": clip, "startFrame": 0, "endFrame": 0, "mediaType": 1}],
    ]:
        try:
            if mp.AppendToTimeline(payload):
                return True
        except Exception:
            continue
    return False


def _save_image(img) -> Path | None:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for folder in (IMAGES_DIR, Path(tempfile.gettempdir())):
        try:
            path = folder / f"mpaste_{ts}.png"
            img.save(str(path), "PNG")
            return path
        except Exception:
            continue
    return None


def _save_gif(src_path: Path) -> Path | None:
    """Copia el GIF a la carpeta de imágenes de MPaste con timestamp."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for folder in (IMAGES_DIR, Path(tempfile.gettempdir())):
        try:
            dst = folder / f"mpaste_{ts}.gif"
            import shutil
            shutil.copy2(str(src_path), str(dst))
            return dst
        except Exception:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ── QWebChannel injection helper ──────────────────────────────────────────────
def _inject_qwebchannel(page) -> None:
    """
    Inject qwebchannel.js into a QWebEnginePage.

    Uses setSourceCode() with content read from Qt's resource system via QFile.
    This is the only reliable method in Qt 6 when HTML is loaded from file://,
    because <script src="qrc:///..."> is blocked by cross-origin policy between
    the qrc:// and file:// schemes.
    """
    from PySide6.QtWebEngineCore import QWebEngineScript
    from PySide6.QtCore import QFile, QIODevice
    f = QFile(":/qtwebchannel/qwebchannel.js")
    if not f.open(QIODevice.OpenModeFlag.ReadOnly):
        print("[MPaste] WARNING: qrc:/qtwebchannel/qwebchannel.js not found")
        return
    content = bytes(f.readAll()).decode("utf-8")
    f.close()
    s = QWebEngineScript()
    s.setName("mpaste-qwebchannel")
    s.setSourceCode(content)
    s.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    s.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    page.scripts().insert(s)


# ── Dependency check (dev mode) ──────────────────────────────────────────────
def _check_deps() -> list[str]:
    """Return list of missing packages. Empty = all good."""
    missing = []
    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("Pillow  →  pip install Pillow")
    if _OS == "Windows":
        try:
            import win32clipboard  # noqa: F401
        except ImportError:
            missing.append("pywin32  →  pip install pywin32")
    return missing


# BLOCK 5 — Backend (QWebChannel API)
# ══════════════════════════════════════════════════════════════════════════════
from PySide6.QtCore    import QObject, Slot
from PySide6.QtWidgets import QApplication


class Backend(QObject):
    def __init__(self, window):
        super().__init__()
        self._win = window

    # ── Window ───────────────────────────────────────────────────────────────────
    @Slot()
    def start_move(self):
        try:
            h = self._win.windowHandle()
            if h:
                h.startSystemMove()
        except Exception:
            pass

    @Slot()
    def minimize_window(self):
        try:
            self._win.showMinimized()
        except Exception:
            pass

    @Slot()
    def close_window(self):
        try:
            self._win.close()
        except Exception:
            pass

    @Slot()
    def focus_window(self):
        """Usado por el guard de instancia para enfocar la ventana existente."""
        try:
            from PySide6.QtCore import Qt
            self._win.setWindowState(
                self._win.windowState() & ~Qt.WindowState.WindowMinimized
            )
            self._win.raise_()
            self._win.activateWindow()
        except Exception:
            pass

    # ── Settings ─────────────────────────────────────────────────────────────────
    @Slot(result=str)
    def get_settings(self):
        return json.dumps(_load_settings())

    @Slot(str, result=str)
    def save_settings(self, data_json):
        try:
            ok = _save_settings(json.loads(data_json))
            return json.dumps({"ok": ok})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @Slot(result=str)
    def get_system_lang(self):
        try:
            import locale
            loc = locale.getlocale()[0] or locale.getdefaultlocale()[0] or "en"
            lang = loc.split("_")[0].lower()
            return lang if lang in _VALID_LANGS else "en"
        except Exception:
            return "en"

    @Slot(result=str)
    def get_fonts_base_url(self):
        fonts_dir = Path(_BUNDLE_DIR) / "fonts"
        if not fonts_dir.is_dir():
            fonts_dir = Path(_SCRIPT_DIR) / "fonts"
        if fonts_dir.is_dir() and any(fonts_dir.glob("*.ttf")):
            return "file:///" + str(fonts_dir).replace("\\", "/")
        return ""

    @Slot(bool, result=str)
    def set_always_on_top(self, value):
        try:
            from PySide6.QtCore import Qt
            flag = Qt.WindowType.WindowStaysOnTopHint
            flags = self._win.windowFlags()
            if value:
                self._win.setWindowFlags(flags | flag)
            else:
                self._win.setWindowFlags(flags & ~flag)
            self._win.show()
            s = _load_settings()
            s["always_on_top"] = bool(value)
            _save_settings(s)
            return json.dumps({"ok": True})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    # ── Settings window ─────────────────────────────────────────────────────────
    @Slot()
    def open_settings(self):
        """Abre ventana de ajustes (QWebEngineView + settings.html)."""
        try:
            from settings_window import SettingsWindow
            win = self._win
            # Reutilizar instancia si ya está visible
            if hasattr(win, '_settings_win') and win._settings_win is not None:
                sw = win._settings_win
                if sw.isVisible():
                    sw.raise_()
                    sw.activateWindow()
                    return
            sw = SettingsWindow(
                cfg=_load_settings(),
                settings_html=SETTINGS_HTML,
                parent=None,
            )
            sw.settings_saved.connect(win._on_settings_saved)
            win._settings_win = sw
            sw.show_near(win)
        except Exception:
            import traceback
            print("open_settings error:", traceback.format_exc())

    # ── Copy frame (Resolve → clipboard) ────────────────────────────────────────
    @Slot(result=str)
    def copy_frame(self):
        """
        Copy the current Resolve frame to the clipboard.

        Primary:  proj.ExportCurrentFrameAsStill(path)  — any page, full resolution.
        Fallback: tl.GetCurrentClipThumbnailImage()      — Color page, base64 RGB data.
        """
        try:
            from PIL import Image
        except ImportError:
            return json.dumps({"level": "error",
                               "msg": "Pillow not installed. Run: pip install Pillow"})

        try:
            resolve, proj, tl = _get_resolve()
        except RuntimeError as e:
            return json.dumps({"level": "error", "msg": str(e)})
        if not tl:
            return json.dumps({"level": "warn", "msg": "No active timeline in Resolve"})

        # Both ExportCurrentFrameAsStill and GetCurrentClipThumbnailImage
        # require the Color page to be active in Resolve.
        orig_page = "edit"
        try:
            orig_page = resolve.GetCurrentPage() or "edit"
            if orig_page != "color":
                resolve.OpenPage("color")
                time.sleep(0.5)
        except Exception:
            pass

        # ── Method 1: ExportCurrentFrameAsStill (full resolution PNG) ────────
        try:
            tmp_path = str(Path(tempfile.gettempdir()) / "mpaste_frame.png")
            ok = proj.ExportCurrentFrameAsStill(tmp_path)
            if ok and os.path.isfile(tmp_path):
                img = Image.open(tmp_path).convert("RGB")
                try: os.unlink(tmp_path)
                except Exception: pass
                if orig_page != "color":
                    try: resolve.OpenPage(orig_page)
                    except Exception: pass
                clipboard_set_image(img)
                return json.dumps({"level": "ok", "msg": "Frame copied to clipboard"})
        except Exception as e:
            print(f"[copy_frame] ExportCurrentFrameAsStill failed: {e}")

        # ── Method 2: GetCurrentClipThumbnailImage (in-memory base64 RGB) ────
        try:
            import base64
            thumb = tl.GetCurrentClipThumbnailImage()
            if thumb and thumb.get("data"):
                raw = base64.b64decode(thumb["data"])
                img = Image.frombytes("RGB", (thumb["width"], thumb["height"]), raw)
                if orig_page != "color":
                    try: resolve.OpenPage(orig_page)
                    except Exception: pass
                clipboard_set_image(img)
                return json.dumps({"level": "ok", "msg": "Frame copied (thumbnail)"})
        except Exception as e:
            print(f"[copy_frame] thumbnail fallback failed: {e}")

        # Restore page before giving up
        try:
            if orig_page != "color":
                resolve.OpenPage(orig_page)
        except Exception:
            pass

        # ── Method 3: static image file of the active clip ────────────────────
        try:
            item    = tl.GetCurrentVideoItem()
            mp_item = item.GetMediaPoolItem() if item else None
            fpath   = mp_item.GetClipProperty("File Path") if mp_item else None
            if fpath and os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
                    clipboard_set_image(Image.open(fpath))
                    return json.dumps({"level": "ok", "msg": "Clip image copied"})
        except Exception as e:
            print(f"[copy_frame] static fallback failed: {e}")

        return json.dumps({"level": "error",
                           "msg": "Could not capture frame. Is a clip selected?"})

    # ── Paste image/GIF (clipboard → Resolve) ───────────────────────────────────
    @Slot(result=str)
    def paste_image(self):
        """
        Paste clipboard image/GIF into the active Resolve timeline.
        - Static image (PNG/JPG/etc.): save as PNG → ImportMedia → timeline.
        - GIF: copy to IMAGES_DIR → ImportMedia → timeline (Resolve supports GIF natively).
        """
        try:
            from PIL import Image
        except ImportError:
            return json.dumps({"level": "error",
                               "msg": "Pillow not installed. Run: pip install Pillow"})

        try:
            img, fmt = clipboard_get_image()
        except Exception as e:
            return json.dumps({"level": "error", "msg": f"Clipboard read error: {e}"})

        if img is None:
            return json.dumps({"level": "warn", "msg": "Clipboard empty or no image found"})

        # ── GIF path ──────────────────────────────────────────────────────────
        if isinstance(fmt, str) and fmt.startswith("gif:"):
            src_gif = Path(fmt[4:])
            if not src_gif.is_file():
                return json.dumps({"level": "error", "msg": f"GIF not found: {src_gif}"})
            saved_path = _save_gif(src_gif)
            if not saved_path:
                return json.dumps({"level": "error", "msg": "Could not copy GIF to disk"})
            return self._import_to_resolve(str(saved_path))

        # ── Static image ──────────────────────────────────────────────────────
        try:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
        except Exception as e:
            return json.dumps({"level": "error", "msg": f"Image conversion failed: {e}"})

        saved_path = _save_image(img)
        if not saved_path:
            return json.dumps({"level": "error", "msg": "Could not save image to disk"})

        return self._import_to_resolve(str(saved_path))

    def _import_to_resolve(self, file_path: str) -> str:
        """
        Import file_path to the Media Pool and insert it at the current playhead.
        Finds the first video track free at the playhead; creates a new track if needed.
        Falls back to AppendToTimeline (end of timeline) if playhead logic fails.
        """
        try:
            resolve, proj, tl = _get_resolve()
        except RuntimeError as e:
            return json.dumps({"level": "error", "msg": str(e)})

        # Ensure Edit page so the timeline is active
        try:
            cur = resolve.GetCurrentPage() or ""
            if cur not in ("edit", "cut"):
                resolve.OpenPage("edit")
                time.sleep(0.5)
            # Refresh after page switch
            pm   = resolve.GetProjectManager()
            proj = pm.GetCurrentProject()
            tl   = proj.GetCurrentTimeline() if proj else None
        except Exception:
            pass

        # Import to Media Pool
        try:
            mp    = proj.GetMediaPool()
            clips = mp.ImportMedia([file_path])
        except Exception as e:
            return json.dumps({"level": "error", "msg": f"ImportMedia failed: {e}"})

        if not clips:
            return json.dumps({"level": "error", "msg": "Resolve rejected the file"})

        bin_name = "Media Pool"
        try:
            bin_name = mp.GetCurrentFolder().GetName() or "Media Pool"
        except Exception:
            pass

        if not tl:
            return json.dumps({"level": "warn",
                               "msg": f"Imported to '{bin_name}' (no active timeline)"})

        # ── Insert at playhead on the first free video track ──────────────────
        playhead_frame: int | None = None
        try:
            tc_str  = tl.GetCurrentTimecode()
            fps_raw = str(tl.GetSetting("timelineFrameRate") or "24")
            fps     = float(fps_raw.replace("DF", "").strip())
            playhead_frame = _tc_to_frames(tc_str, fps)
        except Exception as e:
            print(f"[_import_to_resolve] playhead read failed: {e}")

        if playhead_frame is not None:
            try:
                track_idx = _find_free_video_track(tl, playhead_frame)
                ok = _insert_at_frame(mp, clips[0], playhead_frame, track_idx)
                if ok:
                    return json.dumps({"level": "ok",
                                       "msg": f"Pasted at playhead (track {track_idx})"})
            except Exception as e:
                print(f"[_import_to_resolve] insert at playhead failed: {e}")

        # ── Fallback: append at end of timeline ───────────────────────────────
        if _append_clip(mp, clips[0]):
            return json.dumps({"level": "ok", "msg": f"Appended to '{bin_name}'"})

        return json.dumps({"level": "warn",
                           "msg": f"Imported to '{bin_name}' (couldn't add to timeline)"})


# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 6 — Single-instance guard (QLocalServer)
# ══════════════════════════════════════════════════════════════════════════════
"""
Estrategia: QLocalServer con nombre único por usuario.

- Primera instancia: crea el servidor y sigue normal.
- Segunda instancia: conecta al servidor existente, envía "focus",
  y sale inmediatamente.
- Primera instancia recibe "focus" y llama window.focus_window().

Ventajas sobre otras estrategias:
  ✓ Cross-platform (Win/Mac/Linux) sin syscalls específicos.
  ✓ No deja archivos de lock huérfanos tras crash (QLocalServer los limpia).
  ✓ Permite enviar comandos (no solo "ya existe").
  ✓ No necesita permisos de administrador.
"""

from PySide6.QtNetwork import QLocalServer, QLocalSocket

_INSTANCE_KEY = "MPaste_MMarket_SingleInstance"


def _try_focus_existing() -> bool:
    """Intenta conectar a una instancia existente. Devuelve True si la encontró."""
    sock = QLocalSocket()
    sock.connectToServer(_INSTANCE_KEY)
    if sock.waitForConnected(500):
        sock.write(b"focus")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def _start_instance_server(window) -> QLocalServer:
    """Crea el servidor de instancia única y conecta la señal de foco."""
    server = QLocalServer()
    # Limpiar socket anterior si quedó huérfano (crash previo)
    QLocalServer.removeServer(_INSTANCE_KEY)
    server.listen(_INSTANCE_KEY)

    def _on_new_connection():
        conn = server.nextPendingConnection()
        if not conn:
            return
        conn.waitForReadyRead(300)
        msg = bytes(conn.readAll()).strip()
        conn.disconnectFromServer()
        if msg == b"focus":
            try:
                from PySide6.QtCore import Qt
                window.setWindowState(
                    window.windowState() & ~Qt.WindowState.WindowMinimized
                )
                window.raise_()
                window.activateWindow()
            except Exception:
                pass

    server.newConnection.connect(_on_new_connection)
    return server


# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 7 — Main window
# ══════════════════════════════════════════════════════════════════════════════
from PySide6.QtWidgets          import QMainWindow, QSizeGrip
from PySide6.QtWebEngineWidgets  import QWebEngineView
from PySide6.QtWebEngineCore     import QWebEngineScript, QWebEngineSettings
from PySide6.QtWebChannel        import QWebChannel
from PySide6.QtCore              import Qt, QUrl
from PySide6.QtGui               import QColor, QPainter, QBrush




class _ThemedGrip(QSizeGrip):
    """
    QSizeGrip subclass that paints a dot-matrix resize indicator
    in the current theme's subtle text color instead of the OS default.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#555555")

    def set_color(self, hex_color: str):
        self._color = QColor(hex_color)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        w, h = self.width(), self.height()
        dot, gap = 2, 3
        for row in range(3):
            for col in range(3):
                if row + col >= 2:          # bottom-right triangle pattern
                    x = w - (col + 1) * gap - dot
                    y = h - (row + 1) * gap - dot
                    if x >= 0 and y >= 0:
                        p.drawRoundedRect(x, y, dot, dot, 1, 1)


class MPasteWindow(QMainWindow):
    # Default and minimum window dimensions
    DEFAULT_W = 252
    DEFAULT_H = 210
    MIN_W     = 180
    MIN_H     = 160

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MPaste")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.resize(self.DEFAULT_W, self.DEFAULT_H)

        # App / taskbar icon
        self._set_icon()

        s = _load_settings()
        if s.get("always_on_top", True):
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )

        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        # Resize grip (bottom-right corner) for frameless window
        self._grip = _ThemedGrip(self)
        self._grip.setFixedSize(12, 12)
        self._grip.raise_()

        self._channel = QWebChannel()
        self._backend = Backend(self)
        self._channel.registerObject("backend", self._backend)
        self._view.page().setWebChannel(self._channel)

        # GPU acceleration
        _ws = self._view.page().settings()
        _ws.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        _ws.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # Inject qwebchannel.js via setSourceCode (reliable for file:// pages in Qt 6)
        _inject_qwebchannel(self._view.page())

        self._settings_win = None  # reusable SettingsWindow instance

        if UI_FILE.is_file():
            self._view.setUrl(QUrl.fromLocalFile(str(UI_FILE)))
        else:
            self._view.setHtml(
                "<body style='background:#0a0a0a;color:#e05c5c;"
                "font-family:monospace;padding:24px'>"
                f"<h2>ui.html not found</h2><p>{UI_FILE}</p></body>"
            )

    def resizeEvent(self, event):
        """Keep the resize grip pinned to the bottom-right corner."""
        super().resizeEvent(event)
        self._grip.move(self.width() - self._grip.width(),
                        self.height() - self._grip.height())

    def _set_icon(self):
        """Load icon from bundle dir or script dir; set on window and taskbar."""
        from PySide6.QtGui import QIcon
        for candidate in [
            Path(_BUNDLE_DIR) / "MPaste.ico",
            Path(_SCRIPT_DIR) / "MPaste.ico",
            Path(_BUNDLE_DIR) / "icons" / "MPaste.ico",
            Path(_SCRIPT_DIR) / "icons"  / "MPaste.ico",
        ]:
            if candidate.is_file():
                icon = QIcon(str(candidate))
                self.setWindowIcon(icon)
                QApplication.instance().setWindowIcon(icon)
                return

    def _on_settings_saved(self, new_cfg: dict):
        """Apply and persist settings received from SettingsWindow."""
        _save_settings(new_cfg)
        # Apply always_on_top to main window immediately
        aot = bool(new_cfg.get("always_on_top", True))
        flag = Qt.WindowType.WindowStaysOnTopHint
        flags = self.windowFlags()
        if aot:
            self.setWindowFlags(flags | flag)
        else:
            self.setWindowFlags(flags & ~flag)
        self.show()
        # Tell WebView to update theme/font/language without reloading
        cfg_json = json.dumps(new_cfg).replace("'", "\'")
        self._view.page().runJavaScript(
            f"if(typeof applySettings==='function'){{Object.assign(cfg,{cfg_json});applySettings(false);}}"
        )
        # Update resize grip color to match the new theme
        theme = new_cfg.get("theme", "mmarket")
        self._grip.set_color(_THEME_TX3.get(theme, "#555555"))


# ══════════════════════════════════════════════════════════════════════════════
# BLOCK 8 — Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # ── CLI flags for Inno Setup ─────────────────────────────────────────────
    # Called by installer/uninstaller — no window opened.
    if "--install-lua" in sys.argv:
        from install import install_lua
        install_lua()
        sys.exit(0)
    if "--uninstall-lua" in sys.argv:
        from install import uninstall_lua
        uninstall_lua()
        sys.exit(0)

    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--enable-gpu-rasterization --enable-zero-copy "
        "--ignore-gpu-blocklist --enable-oop-rasterization",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MPaste")
    app.setOrganizationName("MMarket")
    app.setApplicationDisplayName("MPaste")
    # AA_UseHighDpiPixmaps removed: deprecated in Qt 6, now the default behaviour
    app.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    # Set app icon early so it shows in the taskbar before the window appears
    from PySide6.QtGui import QIcon
    for _ico in [Path(_BUNDLE_DIR) / "MPaste.ico",
                 Path(_SCRIPT_DIR) / "MPaste.ico"]:
        if _ico.is_file():
            app.setWindowIcon(QIcon(str(_ico)))
            break

    # Single-instance guard: try to focus existing instance first
    if _try_focus_existing():
        sys.exit(0)

    # Warn about missing optional deps — shown in console, not blocking
    _missing = _check_deps()
    if _missing:
        print("[MPaste] Missing dependencies:")
        for m in _missing:
            print(f"  {m}")

    window = MPasteWindow()
    window.show()

    # Start instance server AFTER showing the window
    _instance_server = _start_instance_server(window)

    sys.exit(app.exec())
