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
# BLOQUE 0 — freeze_support (DEBE ir antes de cualquier import pesado)
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
# BLOQUE 1 — Rutas
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

# Resolver ui.html y settings.html — dev prioriza carpeta de main.py
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
# BLOQUE 2 — Resolve modules en sys.path
# ══════════════════════════════════════════════════════════════════════════════
for _rp in get_resolve_module_paths():
    _rp = str(_rp)
    if os.path.isdir(_rp) and _rp not in sys.path:
        sys.path.insert(0, _rp)

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — Settings
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULT_SETTINGS = {
    "accent":        "#f5c842",
    "theme":         "mmarket",
    "font":          "barlow",
    "lang":          "es",
    "always_on_top": True,
}

_VALID_THEMES = {"mmarket", "rosepine", "gruvbox"}
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
# BLOQUE 4 — Helpers de Resolve
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
# BLOQUE 5 — Backend (QWebChannel API)
# ══════════════════════════════════════════════════════════════════════════════
from PySide6.QtCore    import QObject, Slot
from PySide6.QtWidgets import QApplication


class Backend(QObject):
    def __init__(self, window):
        super().__init__()
        self._win = window

    # ── Ventana ──────────────────────────────────────────────────────────────
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

    # ── Settings ─────────────────────────────────────────────────────────────
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

    # ── Settings window ──────────────────────────────────────────────────────
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

    # ── Copy frame (Resolve → clipboard) ─────────────────────────────────────
    @Slot(result=str)
    def copy_frame(self):
        try:
            resolve, proj, tl = _get_resolve()
        except RuntimeError as e:
            return json.dumps({"level": "error", "msg": str(e)})
        if not tl:
            return json.dumps({"level": "warn", "msg": "Sin timeline activa en Resolve"})

        orig_page = "edit"
        try:
            orig_page = resolve.GetCurrentPage() or "edit"
        except Exception:
            pass

        def _restore():
            try:
                resolve.OpenPage(orig_page)
            except Exception:
                pass

        try:
            resolve.OpenPage("color")
            time.sleep(0.6)
            still = tl.GrabStill()
            if still:
                gallery = proj.GetGallery()
                album   = gallery.GetCurrentStillAlbum() if gallery else None
                if album:
                    tmp_dir = tempfile.mkdtemp(prefix="mpaste_")
                    album.ExportStills([still], tmp_dir, "frame", "png")
                    pngs     = []
                    deadline = time.time() + 12.0
                    while time.time() < deadline:
                        time.sleep(0.35)
                        pngs = glob.glob(os.path.join(tmp_dir, "*.png"))
                        if pngs:
                            break
                    if pngs:
                        from PIL import Image
                        img = Image.open(max(pngs, key=os.path.getmtime)).convert("RGB")
                        clipboard_set_image(img)
                        try:
                            album.DeleteStills([still])
                        except Exception:
                            pass
                        _restore()
                        return json.dumps({"level": "ok", "msg": "Frame copiado al portapapeles"})
        except Exception:
            pass

        _restore()

        # Fallback: imagen estática del clip activo
        try:
            item    = tl.GetCurrentVideoItem()
            mp_item = item.GetMediaPoolItem() if item else None
            fpath   = mp_item.GetClipProperty("File Path") if mp_item else None
            if fpath and os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
                    from PIL import Image
                    clipboard_set_image(Image.open(fpath))
                    return json.dumps({"level": "ok", "msg": "Imagen del clip copiada (fallback)"})
        except Exception:
            pass

        return json.dumps({"level": "warn", "msg": "Abre página Color en Resolve e intenta"})

    # ── Paste image/GIF (clipboard → Resolve) ────────────────────────────────
    @Slot(result=str)
    def paste_image(self):
        """
        Lee el clipboard.
        - Imagen estática (PNG/JPG/etc.): guarda como PNG → ImportMedia → timeline.
        - GIF: copia el archivo GIF a IMAGES_DIR → ImportMedia → timeline.
          DaVinci Resolve soporta GIF nativo; se inserta como clip de video.
        """
        try:
            img, fmt = clipboard_get_image()
        except Exception as e:
            return json.dumps({"level": "error", "msg": f"Error leyendo portapapeles: {e}"})

        if img is None:
            return json.dumps({"level": "warn", "msg": "Portapapeles vacío o sin imagen válida"})

        # ── Caso GIF ──────────────────────────────────────────────────────────
        if isinstance(fmt, str) and fmt.startswith("gif:"):
            src_gif = Path(fmt[4:])
            if not src_gif.is_file():
                return json.dumps({"level": "error", "msg": f"GIF no encontrado: {src_gif}"})

            saved_path = _save_gif(src_gif)
            if not saved_path:
                return json.dumps({"level": "error", "msg": "No se pudo copiar el GIF a disco"})

            return self._import_to_resolve(str(saved_path))

        # ── Caso imagen estática ──────────────────────────────────────────────
        try:
            from PIL import Image
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
        except Exception as e:
            return json.dumps({"level": "error", "msg": f"No se pudo convertir imagen: {e}"})

        saved_path = _save_image(img)
        if not saved_path:
            return json.dumps({"level": "error", "msg": "No se pudo guardar la imagen en disco"})

        return self._import_to_resolve(str(saved_path))

    def _import_to_resolve(self, file_path: str) -> str:
        """Importa file_path al MediaPool y lo agrega a la timeline activa."""
        try:
            resolve, proj, tl = _get_resolve()
        except RuntimeError as e:
            return json.dumps({"level": "error", "msg": str(e)})

        # Asegurar página Edit
        try:
            cur = resolve.GetCurrentPage() or ""
            if cur not in ("edit", "cut"):
                resolve.OpenPage("edit")
                time.sleep(0.5)
        except Exception:
            pass

        # Refrescar proj/tl por si cambió de página
        try:
            pm   = resolve.GetProjectManager()
            proj = pm.GetCurrentProject()
            tl   = proj.GetCurrentTimeline() if proj else None
        except Exception:
            tl = None

        try:
            mp    = proj.GetMediaPool()
            clips = mp.ImportMedia([file_path])
        except Exception as e:
            return json.dumps({"level": "error", "msg": f"ImportMedia falló: {e}"})

        if not clips:
            return json.dumps({"level": "error", "msg": "Resolve rechazó el archivo"})

        bin_name = "Media Pool"
        try:
            bin_name = mp.GetCurrentFolder().GetName() or "Media Pool"
        except Exception:
            pass

        if not tl:
            return json.dumps({"level": "warn", "msg": f"En '{bin_name}' (sin timeline activa)"})

        added = _append_clip(mp, clips[0])
        if added:
            return json.dumps({"level": "ok", "msg": f"Pegado en '{bin_name}'"})
        return json.dumps({"level": "warn", "msg": f"En '{bin_name}' (no se pudo agregar a timeline)"})


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 6 — Guard de instancia única (QLocalServer)
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
# BLOQUE 7 — Ventana principal
# ══════════════════════════════════════════════════════════════════════════════
from PySide6.QtWidgets          import QMainWindow
from PySide6.QtWebEngineWidgets  import QWebEngineView
from PySide6.QtWebEngineCore     import QWebEngineScript, QWebEngineSettings
from PySide6.QtWebChannel        import QWebChannel
from PySide6.QtCore              import Qt, QUrl




class MPasteWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MPaste")
        self.setFixedSize(252, 210)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        s = _load_settings()
        if s.get("always_on_top", True):
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )

        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        self._channel = QWebChannel()
        self._backend = Backend(self)
        self._channel.registerObject("backend", self._backend)
        self._view.page().setWebChannel(self._channel)

        # Aceleración GPU
        _ws = self._view.page().settings()
        _ws.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        _ws.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # Inyectar qwebchannel.js
        script = QWebEngineScript()
        script.setSourceUrl(QUrl("qrc:/qtwebchannel/qwebchannel.js"))
        script.setName("mpaste-qwebchannel")
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        self._view.page().scripts().insert(script)

        self._settings_win = None  # instancia reutilizable de SettingsWindow

        if UI_FILE.is_file():
            self._view.setUrl(QUrl.fromLocalFile(str(UI_FILE)))
        else:
            self._view.setHtml(
                "<body style='background:#0a0a0a;color:#e05c5c;"
                "font-family:monospace;padding:24px'>"
                f"<h2>ui.html no encontrado</h2><p>{UI_FILE}</p></body>"
            )

    def _on_settings_saved(self, new_cfg: dict):
        """Recibe el dict de ajustes desde SettingsWindow y los persiste."""
        _save_settings(new_cfg)
        # Propagar always_on_top a la ventana principal inmediatamente
        aot = bool(new_cfg.get("always_on_top", True))
        flag = Qt.WindowType.WindowStaysOnTopHint
        flags = self.windowFlags()
        if aot:
            self.setWindowFlags(flags | flag)
        else:
            self.setWindowFlags(flags & ~flag)
        self.show()
        # Notificar a la WebView para que actualice tema/fuente/idioma sin recargar
        cfg_json = json.dumps(new_cfg).replace("'", "\'")
        self._view.page().runJavaScript(
            f"if(typeof applySettings==='function'){{Object.assign(cfg,{cfg_json});applySettings(false);}}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 8 — Punto de entrada
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # ── CLI flags para Inno Setup ──────────────────────────────────────────
    # Invocado por el instalador/desinstalador, no abre ventana.
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
    # AA_UseHighDpiPixmaps eliminado: deprecated en Qt 6, comportamiento por defecto
    app.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    # Guard de instancia única: intentar enfocar la existente primero
    if _try_focus_existing():
        sys.exit(0)

    window = MPasteWindow()
    window.show()

    # Iniciar servidor de instancia única DESPUÉS de mostrar la ventana
    _instance_server = _start_instance_server(window)

    sys.exit(app.exec())
