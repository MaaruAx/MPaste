"""
MPaste - MMarket Ecosystem
MMarket/Apps/MPaste/
"""

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 0 — Ocultar consola
# ══════════════════════════════════════════════════════════════════════════════
import sys
import os

_IS_FROZEN  = getattr(sys, "frozen", False)          # True cuando empaquetado con PyInstaller
_BUNDLE_DIR = getattr(sys, "_MEIPASS", None)          # Carpeta temporal de PyInstaller (archivos embebidos)

_GUARD = "MPASTE_STARTED"
if os.environ.get(_GUARD) != "1":
    os.environ[_GUARD] = "1"
    # Cuando es .exe (PyInstaller con --noconsole) no hay consola que ocultar.
    # El bloque solo aplica cuando se ejecuta como .py normal.
    if not _IS_FROZEN:
        try:
            import ctypes
            _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if _hwnd and _hwnd != 0:
                _is_store = "WindowsApps" in sys.executable
                if not _is_store:
                    _pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                    if os.path.isfile(_pyw):
                        import subprocess as _sp
                        _sp.Popen(
                            [_pyw] + sys.argv,
                            creationflags=0x08000000,
                            close_fds=True,
                            env={**os.environ, _GUARD: "1"},
                        )
                        sys.exit(0)
                ctypes.windll.user32.ShowWindow(_hwnd, 0)
        except SystemExit:
            raise
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — Rutas base
# ══════════════════════════════════════════════════════════════════════════════
# Cuando es .exe frozen: __file__ no existe o apunta a sys._MEIPASS.
# _SCRIPT_DIR = donde vive el .exe (para escribir Lua, leer settings, etc.)
# _BUNDLE_DIR = donde PyInstaller extrae los archivos embebidos (ui.html, etc.)
if _IS_FROZEN:
    _SCRIPT_DIR = os.path.dirname(sys.executable)
    _BUNDLE_DIR = _BUNDLE_DIR or _SCRIPT_DIR
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE_DIR = _SCRIPT_DIR
_APPDATA    = os.path.expandvars("%APPDATA%")

INSTALL_DIR   = os.path.join(_APPDATA, "MMarket", "Apps", "MPaste")
IMAGES_DIR    = os.path.join(INSTALL_DIR, "images")
CACHE_FILE    = os.path.join(INSTALL_DIR, "deps_cache.json")
SETTINGS_FILE = os.path.join(INSTALL_DIR, "settings.json")

_UI_INSTALLED = os.path.join(INSTALL_DIR, "ui.html")
_UI_BUNDLE    = os.path.join(_BUNDLE_DIR, "ui.html")   # embebido en el .exe
_UI_LOCAL     = os.path.join(_SCRIPT_DIR, "ui.html")

_RESOLVE_SCRIPTS = [
    os.path.join(_APPDATA, "Blackmagic Design", "DaVinci Resolve", "Support",
                 "Fusion", "Scripts", "Utility"),
    os.path.join(_APPDATA, "Blackmagic Design", "DaVinci Resolve", "Support",
                 "Fusion", "Scripts", "Edit"),
    r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility",
]

for _d in (INSTALL_DIR, IMAGES_DIR):
    try:
        os.makedirs(_d, exist_ok=True)
    except Exception:
        pass

import json

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(default) if isinstance(default, dict) else default

def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — Primer arranque: copia + Lua
# ══════════════════════════════════════════════════════════════════════════════
import shutil

_FIRST_RUN_FLAG = os.path.join(INSTALL_DIR, ".initialized")

def _do_first_run():
    if not _IS_FROZEN:
        # Solo cuando se ejecuta como .py: copia los archivos al directorio de instalacion
        for fname in ("main.py", "ui.html"):
            src = os.path.join(_SCRIPT_DIR, fname)
            dst = os.path.join(INSTALL_DIR, fname)
            if os.path.isfile(src) and not os.path.isfile(dst):
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass

    if _IS_FROZEN:
        # .exe: el Lua llama directamente al ejecutable
        exe_path = sys.executable.replace("\\", "\\\\")
        lua_content = (
            '-- MPaste launcher para DaVinci Resolve\n'
            '-- Generado automaticamente por MPaste (MMarket)\n'
            'local cmd = string.format(\'"' + exe_path + '"\')\n'
            'os.execute(cmd)\n'
        )
    else:
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(pyw):
            pyw = "pythonw"
        pyw = pyw.replace("\\", "\\\\")
        main_path = os.path.join(INSTALL_DIR, "main.py").replace("\\", "\\\\")
        lua_content = (
            '-- MPaste launcher para DaVinci Resolve\n'
            '-- Generado automaticamente por MPaste (MMarket)\n'
            'local cmd = string.format(\'"' + pyw + '" "' + main_path + '"\')\n'
            'os.execute(cmd)\n'
        )

    for scripts_dir in _RESOLVE_SCRIPTS:
        try:
            os.makedirs(scripts_dir, exist_ok=True)
            lua_path = os.path.join(scripts_dir, "MPaste.lua")
            if not os.path.isfile(lua_path):
                with open(lua_path, "w", encoding="utf-8") as f:
                    f.write(lua_content)
            break
        except Exception:
            continue

    try:
        with open(_FIRST_RUN_FLAG, "w") as f:
            f.write("1")
    except Exception:
        pass

if not os.path.isfile(_FIRST_RUN_FLAG):
    _do_first_run()
else:
    for fname in ("ui.html",):
        src = os.path.join(_SCRIPT_DIR, fname)
        dst = os.path.join(INSTALL_DIR, fname)
        try:
            if os.path.isfile(src) and (
                not os.path.isfile(dst) or
                os.path.getmtime(src) > os.path.getmtime(dst)
            ):
                shutil.copy2(src, dst)
        except Exception:
            pass

if _IS_FROZEN:
    # Frozen: preferir el embebido en el bundle, luego el instalado
    UI_FILE = _UI_BUNDLE if os.path.isfile(_UI_BUNDLE) else _UI_INSTALLED
else:
    # .py: preferir el instalado (para recibir updates), luego el local
    UI_FILE = _UI_INSTALLED if os.path.isfile(_UI_INSTALLED) else _UI_LOCAL


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — Cache de dependencias e instalacion
# ══════════════════════════════════════════════════════════════════════════════
import importlib
import subprocess
import threading

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception as e:
    try:
        with open(os.path.join(os.path.expandvars("%TEMP%"), "mpaste_error.txt"), "w") as f:
            f.write(f"tkinter failed: {e}\n")
    except Exception:
        pass
    sys.exit(1)


def _show_fatal(msg):
    try:
        r = tk.Tk(); r.withdraw()
        messagebox.showerror("MPaste - Error critico", msg, parent=r)
        r.destroy()
    except Exception:
        pass
    sys.exit(1)


def _is_importable(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False

def _pip_install(pkg):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg,
             "--quiet", "--disable-pip-version-check", "--no-warn-script-location"],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout (120s)"
    except Exception as ex:
        return False, str(ex)


_REQUIRED = [("Pillow", "PIL"), ("pywebview", "webview"), ("pywin32", "win32clipboard")]
_OPTIONAL = [("cairosvg", "cairosvg")]

_cache = _load_json(CACHE_FILE, {})

_need_install = []
for pkg, mod in _REQUIRED:
    if _cache.get(pkg) == "ok" and _is_importable(mod):
        continue
    if not _is_importable(mod):
        _need_install.append((pkg, mod, False))
    else:
        _cache[pkg] = "ok"

for pkg, mod in _OPTIONAL:
    if _cache.get(pkg) in ("ok", "skip"):
        continue
    if not _is_importable(mod):
        _need_install.append((pkg, mod, True))
    else:
        _cache[pkg] = "ok"

_save_json(CACHE_FILE, _cache)

if _need_install:
    try:
        _rl = tk.Tk()
        _rl.title("MPaste")
        _rl.geometry("290x114")
        _rl.resizable(False, False)
        _rl.configure(bg="#0a0a0a")
        _rl.attributes("-topmost", True)
        _rl.overrideredirect(True)

        _tb = tk.Frame(_rl, bg="#111111", height=36)
        _tb.pack(fill="x"); _tb.pack_propagate(False)
        tk.Label(_tb, text="  MPASTE", bg="#111111", fg="#f5c842",
                 font=("Impact", 13), anchor="w").pack(side="left", pady=7)
        tk.Label(_tb, text="Instalando  ", bg="#111111", fg="#333333",
                 font=("Segoe UI", 7)).pack(side="right", pady=7)
        tk.Frame(_rl, bg="#2a2a2a", height=2).pack(fill="x")

        _bd = tk.Frame(_rl, bg="#0a0a0a")
        _bd.pack(fill="both", expand=True, padx=12, pady=10)
        _lbl = tk.Label(_bd, text="Preparando...", bg="#0a0a0a", fg="#555555",
                        font=("Segoe UI", 8), anchor="w")
        _lbl.pack(fill="x")

        _sty = ttk.Style(); _sty.theme_use("default")
        _sty.configure("M.Horizontal.TProgressbar",
                       background="#f5c842", troughcolor="#1a1a1a",
                       bordercolor="#2a2a2a", lightcolor="#f5c842",
                       darkcolor="#f5c842", thickness=6)
        _bar = ttk.Progressbar(_bd, style="M.Horizontal.TProgressbar",
                               length=266, mode="determinate",
                               maximum=max(len(_need_install), 1))
        _bar.pack(fill="x", pady=(7, 0))

        def _ds(e): _rl._dx = e.x; _rl._dy = e.y
        def _dm(e): _rl.geometry(
            f"+{_rl.winfo_x()+e.x-_rl._dx}+{_rl.winfo_y()+e.y-_rl._dy}")
        _tb.bind("<ButtonPress-1>", _ds); _tb.bind("<B1-Motion>", _dm)

        _failed = []

        def _worker():
            nc = dict(_cache)
            for i, (pkg, mod, opt) in enumerate(_need_install):
                _rl.after(0, lambda p=pkg, o=opt: _lbl.config(
                    text=f"Instalando {p}{'  (opcional)' if o else ''}..."
                ))
                ok, err = _pip_install(pkg)
                importlib.invalidate_caches()
                if ok and _is_importable(mod):
                    nc[pkg] = "ok"
                elif opt:
                    nc[pkg] = "skip"
                else:
                    _failed.append((pkg, err))
                _rl.after(0, lambda v=i+1: _bar.config(value=v))
            _save_json(CACHE_FILE, nc)
            _rl.after(300, _rl.destroy)

        _t = threading.Thread(target=_worker, daemon=True)
        _t.start(); _rl.mainloop(); _t.join()
        importlib.invalidate_caches()

        if _failed:
            lines = "\n".join(f"  - {p}: {e or 'desconocido'}" for p, e in _failed)
            _show_fatal(
                f"No se pudieron instalar dependencias:\n\n{lines}\n\n"
                "Soluciones:\n"
                "  1. CMD como administrador:\n"
                "       python -m pip install Pillow pywebview pywin32\n"
                "  2. Verifica tu conexion a internet.\n"
                "  3. Si usas Python de Microsoft Store,\n"
                "     instala Python desde python.org."
            )
    except Exception as ex:
        _show_fatal(f"Error durante instalacion:\n{ex}")


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — Imports criticos
# ══════════════════════════════════════════════════════════════════════════════
try:
    import webview
except ImportError:
    _show_fatal(
        "pywebview no disponible.\n\n"
        "Falta Microsoft Edge WebView2 Runtime:\n"
        "  https://aka.ms/webview2\n\n"
        "Luego: python -m pip install pywebview"
    )
except Exception as ex:
    _show_fatal(f"Error al cargar pywebview:\n{ex}")

try:
    from PIL import Image, ImageGrab
except Exception as ex:
    _show_fatal(f"Error al cargar Pillow:\n{ex}")

try:
    import win32clipboard
except Exception as ex:
    _show_fatal(f"Error al cargar pywin32:\n{ex}")

_HAS_CAIRO = False
_cairosvg  = None
try:
    import cairosvg as _cairosvg
    _HAS_CAIRO = True
except Exception:
    pass


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5 — Resolve + helpers
# ══════════════════════════════════════════════════════════════════════════════
import glob, tempfile, datetime, time, io

_RESOLVE_MOD_PATHS = [
    r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
    r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules",
]
for _rp in _RESOLVE_MOD_PATHS:
    if os.path.isdir(_rp) and _rp not in sys.path:
        sys.path.insert(0, _rp)


def _get_resolve():
    try:
        import DaVinciResolveScript as dvr
    except ImportError:
        raise RuntimeError(
            "DaVinciResolveScript no encontrado.\n"
            "MPaste requiere DaVinci Resolve Studio."
        )
    try:
        resolve = dvr.scriptapp("Resolve")
    except Exception as e:
        raise RuntimeError(f"No se pudo conectar a Resolve: {e}")
    if not resolve:
        raise RuntimeError(
            "DaVinci Resolve no responde.\n"
            "Asegurate de que este abierto con un proyecto activo."
        )
    try:
        pm   = resolve.GetProjectManager()
        proj = pm.GetCurrentProject() if pm else None
        if not proj:
            raise RuntimeError("No hay proyecto abierto en Resolve.")
        return resolve, proj, proj.GetCurrentTimeline()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error interno de Resolve: {e}")


def _tc_to_frames(tc_str, fps):
    try:
        tc = str(tc_str).strip().replace(";", ":")
        parts = tc.split(":")
        if len(parts) != 4:
            return 0
        h, m, s, f = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        return int(round((h * 3600 + m * 60 + s) * fps)) + f
    except Exception:
        return 0


def _playhead_record_frame(tl, fps):
    try:
        ph_tc = tl.GetCurrentTimecode()
        st_tc = tl.GetSetting("startTimecode") or "01:00:00:00"
        return max(0, _tc_to_frames(ph_tc, fps) - _tc_to_frames(st_tc, fps))
    except Exception:
        return 0


def _get_still_duration(proj):
    try:
        d = proj.GetSetting("stillsDuration")
        if d:
            return max(1, int(d))
    except Exception:
        pass
    return 100


def _img_to_clipboard(img):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "BMP")
    dib = buf.getvalue()[14:]
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib)
    finally:
        win32clipboard.CloseClipboard()


def _clipboard_to_pil():
    try:
        img = ImageGrab.grabclipboard()
    except Exception:
        img = None

    if isinstance(img, Image.Image):
        return img, "bitmap"

    if isinstance(img, list):
        for path in img:
            if not isinstance(path, str) or not os.path.isfile(path):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext == ".svg" and _HAS_CAIRO:
                try:
                    return Image.open(io.BytesIO(
                        _cairosvg.svg2png(url=path)
                    )).convert("RGBA"), "svg"
                except Exception:
                    pass
            try:
                return Image.open(path), ext.lstrip(".") or "file"
            except Exception:
                continue

    if _HAS_CAIRO:
        try:
            win32clipboard.OpenClipboard()
            try:
                raw = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
            if isinstance(raw, str) and raw.strip().startswith("<svg"):
                return Image.open(io.BytesIO(
                    _cairosvg.svg2png(bytestring=raw.encode("utf-8"))
                )).convert("RGBA"), "svg-text"
        except Exception:
            pass

    return None, None


def _save_image(img):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for folder in (IMAGES_DIR, tempfile.gettempdir()):
        try:
            path = os.path.join(folder, f"mpaste_{ts}.png")
            img.save(path, "PNG")
            return path
        except Exception:
            continue
    return None


def _append_clip(mp, clip):
    """
    Agrega una imagen estatica a la timeline activa.
    Para stills NO se usan startFrame/endFrame: Resolve aplica
    automaticamente su configuracion de duracion de imagenes.
    """
    # Forma 1 — minima: Resolve maneja la duracion (la mas confiable para stills)
    try:
        r = mp.AppendToTimeline([clip])
        if r:
            return True
    except Exception:
        pass

    # Forma 2 — dict sin frames
    try:
        r = mp.AppendToTimeline([{"mediaPoolItem": clip, "mediaType": 1}])
        if r:
            return True
    except Exception:
        pass

    # Forma 3 — dict con frame 0->0 (un solo frame, siempre valido para stills)
    try:
        r = mp.AppendToTimeline([{
            "mediaPoolItem": clip,
            "startFrame":    0,
            "endFrame":      0,
            "mediaType":     1,
        }])
        if r:
            return True
    except Exception:
        pass

    return False


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 6 — API para JavaScript
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULT_SETTINGS = {
    "accent":       "#f5c842",
    "theme":        "dark",
    "lang":         "es",
    "always_on_top": True,
}


class API:

    def get_settings(self):
        try:
            s = _load_json(SETTINGS_FILE, _DEFAULT_SETTINGS)
            for k, v in _DEFAULT_SETTINGS.items():
                s.setdefault(k, v)
            return s
        except Exception:
            return dict(_DEFAULT_SETTINGS)

    def save_settings(self, data):
        try:
            safe = {
                "accent":        str(data.get("accent",  "#f5c842"))[:20],
                "theme":         str(data.get("theme",   "dark"))[:20],
                "lang":          str(data.get("lang",    "es"))[:10],
                "always_on_top": bool(data.get("always_on_top", True)),
            }
            return _save_json(SETTINGS_FILE, safe)
        except Exception:
            return False

    def get_system_lang(self):
        try:
            import locale
            lang = locale.getdefaultlocale()[0] or "en"
            code = lang.split("_")[0].lower()
            return code if code in ("es", "en", "hi") else "en"
        except Exception:
            return "en"

    def set_always_on_top(self, value):
        try:
            win = webview.windows[0] if webview.windows else None
            if win:
                win.on_top = bool(value)
            # Persist immediately
            s = self.get_settings()
            s["always_on_top"] = bool(value)
            _save_json(SETTINGS_FILE, s)
            return True
        except Exception:
            return False

    def minimize(self):
        try:
            win = webview.windows[0] if webview.windows else None
            if win:
                win.minimize()
        except Exception:
            pass

    def copy_frame(self):
        try:
            resolve, proj, tl = _get_resolve()
        except RuntimeError as e:
            return {"level": "error", "msg": str(e)}
        if not tl:
            return {"level": "warn", "msg": "Sin timeline activa en Resolve"}

        orig_page = "edit"
        try:
            orig_page = resolve.GetCurrentPage() or "edit"
        except Exception:
            pass

        def _restore():
            try: resolve.OpenPage(orig_page)
            except Exception: pass

        try:
            resolve.OpenPage("color")
            time.sleep(0.6)           # dar tiempo a que la pagina cargue
            still = tl.GrabStill()
            if still:
                gallery = proj.GetGallery()
                album   = gallery.GetCurrentStillAlbum() if gallery else None
                if album:
                    tmp_dir = tempfile.mkdtemp(prefix="mpaste_")
                    album.ExportStills([still], tmp_dir, "frame", "png")
                    # ExportStills es asincrono: hacer polling hasta que aparezca el archivo
                    pngs     = []
                    deadline = time.time() + 12.0   # hasta 12 segundos
                    while time.time() < deadline:
                        time.sleep(0.35)
                        pngs = glob.glob(os.path.join(tmp_dir, "*.png"))
                        if pngs:
                            break
                    if pngs:
                        img = Image.open(max(pngs, key=os.path.getmtime)).convert("RGB")
                        _img_to_clipboard(img)
                        try: album.DeleteStills([still])
                        except Exception: pass
                        _restore()
                        return {"level": "ok", "msg": "Frame copiado al portapapeles"}
        except Exception:
            pass

        _restore()

        try:
            item    = tl.GetCurrentVideoItem()
            mp_item = item.GetMediaPoolItem() if item else None
            fpath   = mp_item.GetClipProperty("File Path") if mp_item else None
            if fpath and os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
                    _img_to_clipboard(Image.open(fpath))
                    return {"level": "ok", "msg": "Imagen del clip copiada (fallback)"}
        except Exception:
            pass

        return {"level": "warn", "msg": "Abre pagina Color en Resolve e intenta"}

    def paste_image(self):
        # ── 1. Leer portapapeles ──────────────────────────────────────────────
        try:
            img, fmt = _clipboard_to_pil()
        except Exception as e:
            return {"level": "error", "msg": f"Error leyendo portapapeles: {e}"}
        if img is None:
            return {"level": "warn", "msg": "Portapapeles vacio o sin imagen valida"}

        try:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
        except Exception as e:
            return {"level": "error", "msg": f"No se pudo convertir imagen: {e}"}

        # ── 2. Guardar en disco ───────────────────────────────────────────────
        saved_path = _save_image(img)
        if not saved_path:
            return {"level": "error", "msg": "No se pudo guardar la imagen en disco"}

        # ── 3. Conectar a Resolve ─────────────────────────────────────────────
        try:
            resolve, proj, _ = _get_resolve()
        except RuntimeError as e:
            return {"level": "error", "msg": str(e)}

        # ── 4. Cambiar a pagina Edit ANTES de todo (AppendToTimeline lo necesita)
        try:
            cur = resolve.GetCurrentPage() or ""
            if cur not in ("edit", "cut"):
                resolve.OpenPage("edit")
                time.sleep(0.5)
        except Exception:
            pass

        # Re-fetch despues del cambio de pagina (los objetos anteriores pueden quedar invalidos)
        try:
            pm   = resolve.GetProjectManager()
            proj = pm.GetCurrentProject()
            tl   = proj.GetCurrentTimeline() if proj else None
        except Exception:
            tl = None

        # ── 5. Importar al Media Pool ─────────────────────────────────────────
        try:
            mp    = proj.GetMediaPool()
            clips = mp.ImportMedia([saved_path])
        except Exception as e:
            return {"level": "error", "msg": f"ImportMedia fallo: {e}"}
        if not clips:
            return {"level": "error", "msg": "Resolve rechazo el archivo"}

        bin_name = "Media Pool"
        try:
            bin_name = mp.GetCurrentFolder().GetName() or "Media Pool"
        except Exception:
            pass

        if not tl:
            return {"level": "warn", "msg": f"En '{bin_name}' (sin timeline activa)"}

        # ── 6. Agregar a la timeline ──────────────────────────────────────────
        added = _append_clip(mp, clips[0])

        if added:
            return {"level": "ok",  "msg": f"Pegado en '{bin_name}'"}
        return {"level": "warn",    "msg": f"En '{bin_name}' (no se pudo agregar a timeline)"}

    def close(self):
        try:
            if webview.windows:
                webview.windows[0].destroy()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 7 — Verificar ui.html y lanzar ventana
# ══════════════════════════════════════════════════════════════════════════════
if not os.path.isfile(UI_FILE):
    _show_fatal(
        f"No se encontro ui.html.\n\n"
        f"Buscado en:\n"
        f"  {_BUNDLE_DIR}\n"
        f"  {INSTALL_DIR}\n"
        f"  {_SCRIPT_DIR}\n\n"
        "Si usas el .exe, asegurate de compilarlo con:\n"
        "  --add-data \"ui.html;.\""
    )

_settings_on_start = _load_json(SETTINGS_FILE, _DEFAULT_SETTINGS)
_always_on_top     = bool(_settings_on_start.get("always_on_top", True))

try:
    api    = API()
    ui_url = "file:///" + UI_FILE.replace("\\", "/")

    webview.create_window(
        title            = "MPaste",
        url              = ui_url,
        js_api           = api,
        width            = 252,
        height           = 210,
        resizable        = False,
        frameless        = True,
        on_top           = _always_on_top,
        background_color = "#0a0a0a",
        min_size         = (252, 210),
    )
    webview.start(debug=False)
except Exception as e:
    _show_fatal(
        f"No se pudo abrir la ventana.\n\nError: {e}\n\n"
        "Si el error menciona WebView2:\n"
        "  https://aka.ms/webview2\n\n"
        "Si usas Python de Microsoft Store, instala Python desde python.org."
    )
