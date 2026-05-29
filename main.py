"""
MPaste - MMarket Ecosystem
MMarket/Apps/MPaste/
"""

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 0 — Ocultar consola
# ══════════════════════════════════════════════════════════════════════════════
import sys
import os

_GUARD = "MPASTE_STARTED"
if os.environ.get(_GUARD) != "1":
    os.environ[_GUARD] = "1"
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
# BLOQUE 1 — Rutas
# ══════════════════════════════════════════════════════════════════════════════
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_APPDATA    = os.path.expandvars("%APPDATA%")

INSTALL_DIR   = os.path.join(_APPDATA, "MMarket", "Apps", "MPaste")
IMAGES_DIR    = os.path.join(INSTALL_DIR, "images")
CACHE_FILE    = os.path.join(INSTALL_DIR, "deps_cache.json")
SETTINGS_FILE = os.path.join(INSTALL_DIR, "settings.json")

_UI_INSTALLED = os.path.join(INSTALL_DIR, "ui.html")
_UI_LOCAL     = os.path.join(_SCRIPT_DIR, "ui.html")

_RESOLVE_SCRIPTS = [
    os.path.join(_APPDATA, "Blackmagic Design", "DaVinci Resolve", "Support",
                 "Fusion", "Scripts", "Utility"),
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
# BLOQUE 2 — Primer arranque
# ══════════════════════════════════════════════════════════════════════════════
import shutil

_FIRST_RUN_FLAG = os.path.join(INSTALL_DIR, ".initialized")

def _do_first_run():
    for fname in ("main.py", "ui.html"):
        src = os.path.join(_SCRIPT_DIR, fname)
        dst = os.path.join(INSTALL_DIR, fname)
        if os.path.isfile(src) and not os.path.isfile(dst):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass

    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.isfile(pyw):
        pyw = "pythonw"
    pyw_e       = pyw.replace("\\", "\\\\")
    main_path_e = os.path.join(INSTALL_DIR, "main.py").replace("\\", "\\\\")

    lua = (
        '-- MPaste launcher para DaVinci Resolve\n'
        '-- Generado automaticamente por MPaste (MMarket)\n'
        'local cmd = string.format(\'"' + pyw_e + '" "' + main_path_e + '"\')\n'
        'os.execute(cmd)\n'
    )
    for scripts_dir in _RESOLVE_SCRIPTS:
        try:
            os.makedirs(scripts_dir, exist_ok=True)
            lua_path = os.path.join(scripts_dir, "MPaste.lua")
            if not os.path.isfile(lua_path):
                with open(lua_path, "w", encoding="utf-8") as f:
                    f.write(lua)
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
    # Actualizar ui.html si cambio
    src = os.path.join(_SCRIPT_DIR, "ui.html")
    dst = _UI_INSTALLED
    try:
        if os.path.isfile(src) and (
            not os.path.isfile(dst) or
            os.path.getmtime(src) > os.path.getmtime(dst)
        ):
            shutil.copy2(src, dst)
    except Exception:
        pass

UI_FILE = _UI_INSTALLED if os.path.isfile(_UI_INSTALLED) else _UI_LOCAL


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — Instalacion de dependencias
# ══════════════════════════════════════════════════════════════════════════════
import importlib, subprocess, threading

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
        __import__(mod); return True
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


_REQUIRED = [("Pillow","PIL"), ("pywebview","webview"), ("pywin32","win32clipboard")]
_OPTIONAL = [("cairosvg","cairosvg")]
_cache    = _load_json(CACHE_FILE, {})

_need_install = []
for pkg, mod in _REQUIRED:
    if _cache.get(pkg) == "ok" and _is_importable(mod):
        continue
    if not _is_importable(mod):
        _need_install.append((pkg, mod, False))
    else:
        _cache[pkg] = "ok"

for pkg, mod in _OPTIONAL:
    if _cache.get(pkg) in ("ok","skip"):
        continue
    if not _is_importable(mod):
        _need_install.append((pkg, mod, True))
    else:
        _cache[pkg] = "ok"

_save_json(CACHE_FILE, _cache)

if _need_install:
    try:
        _rl = tk.Tk()
        _rl.title("MPaste"); _rl.geometry("290x114"); _rl.resizable(False,False)
        _rl.configure(bg="#0a0a0a"); _rl.attributes("-topmost",True); _rl.overrideredirect(True)
        _tb = tk.Frame(_rl, bg="#111111", height=36)
        _tb.pack(fill="x"); _tb.pack_propagate(False)
        tk.Label(_tb, text="  MPASTE", bg="#111111", fg="#f5c842", font=("Impact",13), anchor="w").pack(side="left", pady=7)
        tk.Label(_tb, text="Instalando  ", bg="#111111", fg="#333333", font=("Segoe UI",7)).pack(side="right", pady=7)
        tk.Frame(_rl, bg="#2a2a2a", height=2).pack(fill="x")
        _bd = tk.Frame(_rl, bg="#0a0a0a"); _bd.pack(fill="both", expand=True, padx=12, pady=10)
        _lbl = tk.Label(_bd, text="Preparando...", bg="#0a0a0a", fg="#555555", font=("Segoe UI",8), anchor="w")
        _lbl.pack(fill="x")
        _sty = ttk.Style(); _sty.theme_use("default")
        _sty.configure("M.Horizontal.TProgressbar", background="#f5c842", troughcolor="#1a1a1a",
                       bordercolor="#2a2a2a", lightcolor="#f5c842", darkcolor="#f5c842", thickness=6)
        _bar = ttk.Progressbar(_bd, style="M.Horizontal.TProgressbar", length=266,
                               mode="determinate", maximum=max(len(_need_install),1))
        _bar.pack(fill="x", pady=(7,0))

        def _ds(e): _rl._dx=e.x; _rl._dy=e.y
        def _dm(e): _rl.geometry(f"+{_rl.winfo_x()+e.x-_rl._dx}+{_rl.winfo_y()+e.y-_rl._dy}")
        _tb.bind("<ButtonPress-1>",_ds); _tb.bind("<B1-Motion>",_dm)

        _failed = []
        def _worker():
            nc = dict(_cache)
            for i,(pkg,mod,opt) in enumerate(_need_install):
                _rl.after(0, lambda p=pkg,o=opt: _lbl.config(text=f"Instalando {p}{'  (opcional)' if o else ''}..."))
                ok,err = _pip_install(pkg)
                importlib.invalidate_caches()
                if ok and _is_importable(mod): nc[pkg]="ok"
                elif opt: nc[pkg]="skip"
                else: _failed.append((pkg,err))
                _rl.after(0, lambda v=i+1: _bar.config(value=v))
            _save_json(CACHE_FILE, nc)
            _rl.after(300, _rl.destroy)

        _t = threading.Thread(target=_worker, daemon=True)
        _t.start(); _rl.mainloop(); _t.join()
        importlib.invalidate_caches()

        if _failed:
            lines = "\n".join(f"  - {p}: {e or 'desconocido'}" for p,e in _failed)
            _show_fatal(f"No se pudieron instalar dependencias:\n\n{lines}\n\n"
                       "Soluciones:\n  1. CMD como administrador:\n"
                       "       python -m pip install Pillow pywebview pywin32\n"
                       "  2. Verifica tu conexion a internet.\n"
                       "  3. Si usas Python de Microsoft Store, instala desde python.org.")
    except Exception as ex:
        _show_fatal(f"Error durante instalacion:\n{ex}")


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — Imports criticos
# ══════════════════════════════════════════════════════════════════════════════
try:
    import webview
except ImportError:
    _show_fatal("pywebview no disponible.\n\nFalta Microsoft Edge WebView2 Runtime:\n  https://aka.ms/webview2\n\nLuego: python -m pip install pywebview")
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
    import cairosvg as _cairosvg; _HAS_CAIRO = True
except Exception:
    pass


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5 — Helpers Resolve
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
        raise RuntimeError("DaVinciResolveScript no encontrado.\nEl scripting API funciona en Resolve Free y Studio.")
    try:
        resolve = dvr.scriptapp("Resolve")
    except Exception as e:
        raise RuntimeError(f"No se pudo conectar a Resolve: {e}")
    if not resolve:
        raise RuntimeError("DaVinci Resolve no responde.\nAsegurate de que este abierto con un proyecto activo.")
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


def _get_fusion():
    """Devuelve (fusion, comp) o lanza RuntimeError."""
    resolve, proj, tl = _get_resolve()
    try:
        fusion = resolve.Fusion()
        if not fusion:
            raise RuntimeError("No se pudo obtener el objeto Fusion.")
        comp = fusion.GetCurrentComp()
        if not comp:
            raise RuntimeError("No hay composicion activa en Fusion.")
        return fusion, comp
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error al acceder a Fusion: {e}")


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
                    return Image.open(io.BytesIO(_cairosvg.svg2png(url=path))).convert("RGBA"), "svg"
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
                return Image.open(io.BytesIO(_cairosvg.svg2png(bytestring=raw.encode()))).convert("RGBA"), "svg-text"
        except Exception:
            pass
    return None, None


def _save_image(img):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for folder in (IMAGES_DIR, tempfile.gettempdir()):
        try:
            path = os.path.join(folder, f"mpaste_{ts}.png")
            img.save(path, "PNG"); return path
        except Exception:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 6 — API para JavaScript
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULT_SETTINGS = {"accent": "#f5c842", "theme": "dark", "lang": "es"}

# Estado en memoria para EXP y MOD (persiste mientras la ventana esta abierta)
_exp_state = {"tool": None, "param": None}     # {tool_name, param_id}
_mod_state = {"tool": None, "param": None, "modifier_data": None}


class API:

    # ── Settings ───────────────────────────────────────────────────
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
                "accent": str(data.get("accent","#f5c842"))[:20],
                "theme":  str(data.get("theme","dark"))[:20],
                "lang":   str(data.get("lang","es"))[:10],
            }
            return _save_json(SETTINGS_FILE, safe)
        except Exception:
            return False

    # ── IMG: Copiar frame ──────────────────────────────────────────
    def copy_frame(self):
        try:
            resolve, proj, tl = _get_resolve()
        except RuntimeError as e:
            return {"level":"error","msg":str(e)}
        if not tl:
            return {"level":"warn","msg":"Sin timeline activa en Resolve"}

        orig_page = "edit"
        try:
            orig_page = resolve.GetCurrentPage() or "edit"
        except Exception:
            pass

        def _restore():
            try: resolve.OpenPage(orig_page)
            except Exception: pass

        # GrabStill (Free + Studio)
        try:
            resolve.OpenPage("color")
            time.sleep(0.5)
            still = tl.GrabStill()
            if still:
                gallery = proj.GetGallery()
                album   = gallery.GetCurrentStillAlbum() if gallery else None
                if album:
                    tmp_dir = tempfile.mkdtemp(prefix="mpaste_")
                    album.ExportStills([still], tmp_dir, "frame", "png")
                    time.sleep(1.0)
                    pngs = glob.glob(os.path.join(tmp_dir, "*.png"))
                    if pngs:
                        img = Image.open(max(pngs, key=os.path.getmtime)).convert("RGB")
                        _img_to_clipboard(img)
                        try: album.DeleteStills([still])
                        except Exception: pass
                        _restore()
                        return {"level":"ok","msg":"Frame copiado al portapapeles"}
        except Exception:
            pass

        _restore()

        # Fallback: archivo fuente si es imagen estatica
        try:
            item    = tl.GetCurrentVideoItem()
            mp_item = item.GetMediaPoolItem() if item else None
            fpath   = mp_item.GetClipProperty("File Path") if mp_item else None
            if fpath and os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext in (".png",".jpg",".jpeg",".bmp",".tiff",".tif",".webp"):
                    _img_to_clipboard(Image.open(fpath))
                    return {"level":"ok","msg":"Imagen del clip copiada (fallback)"}
        except Exception:
            pass

        return {"level":"warn","msg":"Abre pagina Color en Resolve e intenta"}

    # ── IMG: Pegar imagen ──────────────────────────────────────────
    def paste_image(self):
        try:
            img, fmt = _clipboard_to_pil()
        except Exception as e:
            return {"level":"error","msg":f"Error leyendo portapapeles: {e}"}
        if img is None:
            return {"level":"warn","msg":"Portapapeles vacio o sin imagen valida"}
        try:
            if img.mode not in ("RGB","RGBA"):
                img = img.convert("RGBA")
        except Exception as e:
            return {"level":"error","msg":f"No se pudo convertir imagen: {e}"}

        saved_path = _save_image(img)
        if not saved_path:
            return {"level":"error","msg":"No se pudo guardar la imagen en disco"}

        try:
            _, proj, tl = _get_resolve()
        except RuntimeError as e:
            return {"level":"error","msg":str(e)}

        try:
            mp    = proj.GetMediaPool()
            clips = mp.ImportMedia([saved_path])
        except Exception as e:
            return {"level":"error","msg":f"ImportMedia fallo: {e}"}
        if not clips:
            return {"level":"error","msg":"Resolve rechazo el archivo"}

        bin_name = "Media Pool"
        try:
            bin_name = mp.GetCurrentFolder().GetName() or "Media Pool"
        except Exception:
            pass

        if not tl:
            return {"level":"warn","msg":f"En '{bin_name}' (sin timeline activa)"}

        # Append simple — unico metodo fiable en Resolve 20 Free
        ok = False
        try:
            ok = bool(mp.AppendToTimeline([clips[0]]))
        except Exception:
            pass

        if ok:
            return {"level":"ok","msg":f"Pegado en '{bin_name}' + timeline"}
        return {"level":"warn","msg":f"En '{bin_name}' (fallo al agregar a timeline)"}

    # ── EXP: Capturar herramienta + parametro activo en Fusion ────
    def exp_capture(self):
        """
        Detecta la herramienta activa en Fusion y el parametro seleccionado.
        Guarda tool_name.param_id para usarlo como expresion.
        """
        try:
            _, comp = _get_fusion()
        except RuntimeError as e:
            return {"level":"error","msg":str(e)}

        try:
            # Herramienta activa (ultima seleccionada)
            active = comp.GetToolList(True)   # True = solo seleccionadas
            if not active:
                return {"level":"warn","msg":"Selecciona una herramienta en Fusion"}

            tool = list(active.values())[0]
            tool_name = tool.Name

            # Intentar leer el parametro con foco del inspector
            # GetAttrs devuelve atributos; TOOLB_NameSet tiene los params visibles
            # No hay API directa para "param con foco", asi que listamos inputs
            # y buscamos el primero modificado recientemente o el primero numerico
            inputs = tool.GetInputList()
            param_id = None

            if inputs:
                # Buscar el primer input numerico no-conectado (candidato mas probable)
                for k, inp in inputs.items():
                    try:
                        attrs = inp.GetAttrs()
                        # INPID_InputControl: tipo de control
                        ctrl = attrs.get("INPID_InputControl","")
                        if ctrl in ("SliderControl","ScrewControl","RangeControl",
                                    "CheckboxControl","AngleControl"):
                            param_id = k
                            break
                    except Exception:
                        continue

            if not param_id and inputs:
                # Fallback: primer input disponible
                param_id = list(inputs.keys())[0]

            if not param_id:
                return {"level":"warn","msg":f"{tool_name}: sin parametros detectados"}

            _exp_state["tool"]  = tool_name
            _exp_state["param"] = param_id
            ref = f"{tool_name}.{param_id}"
            return {"level":"ok","msg":f"Capturado: {ref}","ref":ref}

        except Exception as e:
            return {"level":"error","msg":f"Error al capturar: {e}"}

    # ── EXP: Escribir expresion en parametro destino ───────────────
    def exp_link(self):
        """
        En la herramienta/parametro actualmente seleccionado en Fusion,
        escribe la expresion que lo conecta al origen capturado.
        """
        if not _exp_state["tool"] or not _exp_state["param"]:
            return {"level":"warn","msg":"Primero captura un parametro origen"}

        try:
            _, comp = _get_fusion()
        except RuntimeError as e:
            return {"level":"error","msg":str(e)}

        try:
            active = comp.GetToolList(True)
            if not active:
                return {"level":"warn","msg":"Selecciona la herramienta destino en Fusion"}

            dest_tool  = list(active.values())[0]
            dest_name  = dest_tool.Name
            dest_inputs = dest_tool.GetInputList()

            if not dest_inputs:
                return {"level":"warn","msg":f"{dest_name}: sin parametros destino"}

            # Buscar el primer input numerico como destino
            dest_param_id = None
            for k, inp in dest_inputs.items():
                try:
                    attrs = inp.GetAttrs()
                    ctrl  = attrs.get("INPID_InputControl","")
                    if ctrl in ("SliderControl","ScrewControl","RangeControl",
                                "CheckboxControl","AngleControl"):
                        dest_param_id = k
                        break
                except Exception:
                    continue

            if not dest_param_id:
                dest_param_id = list(dest_inputs.keys())[0]

            # La expresion en Fusion usa la sintaxis: ToolName.Input[tiempo]
            # Para enlace en vivo (expression) se usa SetExpression
            dest_input = dest_inputs[dest_param_id]
            expr = f"{_exp_state['tool']}.{_exp_state['param']}"

            try:
                dest_input.SetExpression(expr)
            except Exception as ex:
                return {"level":"error","msg":f"No se pudo escribir expresion: {ex}"}

            return {
                "level": "ok",
                "msg":   f"{dest_name}.{dest_param_id} = {expr}"
            }

        except Exception as e:
            return {"level":"error","msg":f"Error al enlazar: {e}"}

    # ── MOD: Capturar modifier + keyframes ─────────────────────────
    def mod_capture(self):
        """
        Captura el modifier del primer parametro seleccionado en Fusion.
        Guarda tipo, keyframes y curvas para poder recrarlo en otro parametro.
        """
        try:
            _, comp = _get_fusion()
        except RuntimeError as e:
            return {"level":"error","msg":str(e)}

        try:
            active = comp.GetToolList(True)
            if not active:
                return {"level":"warn","msg":"Selecciona una herramienta en Fusion"}

            tool      = list(active.values())[0]
            tool_name = tool.Name
            inputs    = tool.GetInputList()

            if not inputs:
                return {"level":"warn","msg":f"{tool_name}: sin parametros"}

            # Buscar primer input con modifier (HasModifier o con keyframes)
            target_id  = None
            target_inp = None
            mod_data   = None

            for k, inp in inputs.items():
                try:
                    # Intentar leer keyframes: GetConnectedOutput apunta al modifier
                    out = inp.GetConnectedOutput()
                    if out:
                        mod_tool = out.GetTool()
                        if mod_tool:
                            target_id  = k
                            target_inp = inp
                            # Serializar datos del modifier
                            mod_attrs = mod_tool.GetAttrs()
                            mod_type  = mod_attrs.get("TOOLS_RegID","") or mod_tool.ID

                            # Leer keyframes si los tiene
                            keyframes = {}
                            try:
                                kf_list = mod_tool.GetKeyFrames()
                                if kf_list:
                                    for t in kf_list:
                                        try:
                                            keyframes[t] = float(inp[t])
                                        except Exception:
                                            pass
                            except Exception:
                                pass

                            mod_data = {
                                "type":      mod_type,
                                "keyframes": keyframes,
                                "attrs":     {str(k2):str(v2) for k2,v2 in mod_attrs.items()
                                              if isinstance(v2,(int,float,str,bool))},
                            }
                            break
                except Exception:
                    continue

            if not mod_data:
                # Sin modifier formal; capturar valor + cualquier keyframe directo
                for k, inp in inputs.items():
                    try:
                        attrs = inp.GetAttrs()
                        ctrl  = attrs.get("INPID_InputControl","")
                        if ctrl in ("SliderControl","ScrewControl","RangeControl","AngleControl"):
                            target_id = k
                            kf_raw = {}
                            try:
                                kf_list = inp.GetKeyFrames()
                                if kf_list:
                                    for t in kf_list:
                                        try:
                                            kf_raw[t] = float(inp[t])
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                            if kf_raw:
                                mod_data = {"type": "Keyframes", "keyframes": kf_raw, "attrs": {}}
                                break
                    except Exception:
                        continue

            if not mod_data:
                return {"level":"warn","msg":f"{tool_name}.{target_id or '?'}: sin modifier ni keyframes"}

            _mod_state["tool"]          = tool_name
            _mod_state["param"]         = target_id
            _mod_state["modifier_data"] = mod_data

            ref = f"{tool_name}.{target_id} ({mod_data['type']})"
            kf_count = len(mod_data.get("keyframes",{}))
            msg = f"Capturado: {ref}"
            if kf_count:
                msg += f" [{kf_count} KF]"
            return {"level":"ok","msg":msg,"ref":ref}

        except Exception as e:
            return {"level":"error","msg":f"Error al capturar modifier: {e}"}

    # ── MOD: Transferir modifier a parametro destino ───────────────
    def mod_transfer(self):
        """
        Recrea el modifier capturado en el parametro actualmente
        seleccionado en Fusion.
        Nota: Resolve 20 Free soporta AddModifier via scripting API.
        Modifiers con estructuras internas complejas (PathModifier, etc.)
        pueden no transferirse completamente.
        """
        if not _mod_state["modifier_data"]:
            return {"level":"warn","msg":"Primero captura un modifier"}

        try:
            _, comp = _get_fusion()
        except RuntimeError as e:
            return {"level":"error","msg":str(e)}

        try:
            active = comp.GetToolList(True)
            if not active:
                return {"level":"warn","msg":"Selecciona la herramienta destino en Fusion"}

            dest_tool   = list(active.values())[0]
            dest_name   = dest_tool.Name
            dest_inputs = dest_tool.GetInputList()

            if not dest_inputs:
                return {"level":"warn","msg":f"{dest_name}: sin parametros destino"}

            # Elegir primer input numerico como destino
            dest_id  = None
            dest_inp = None
            for k, inp in dest_inputs.items():
                try:
                    attrs = inp.GetAttrs()
                    ctrl  = attrs.get("INPID_InputControl","")
                    if ctrl in ("SliderControl","ScrewControl","RangeControl","AngleControl"):
                        dest_id  = k
                        dest_inp = inp
                        break
                except Exception:
                    continue

            if not dest_inp:
                dest_id  = list(dest_inputs.keys())[0]
                dest_inp = dest_inputs[dest_id]

            mod_data = _mod_state["modifier_data"]
            mod_type = mod_data.get("type","")
            kf       = mod_data.get("keyframes",{})

            applied = False

            # Caso 1: Keyframes directos (sin modifier formal)
            if mod_type == "Keyframes" and kf:
                try:
                    comp.StartUndo("MPaste: Modifier Transfer")
                    for t, v in kf.items():
                        try:
                            dest_inp[int(t)] = float(v)
                        except Exception:
                            pass
                    comp.EndUndo(True)
                    applied = True
                except Exception as ex:
                    try: comp.EndUndo(False)
                    except Exception: pass
                    return {"level":"error","msg":f"Error aplicando keyframes: {ex}"}

            # Caso 2: Modifier con AddModifier
            elif mod_type:
                try:
                    comp.StartUndo("MPaste: Modifier Transfer")
                    new_mod = comp.AddModifier(dest_inp, mod_type)
                    if new_mod and kf:
                        mod_inp_list = new_mod.GetInputList()
                        # Intentar aplicar keyframes al primer input numerico del modifier
                        for mk, minp in (mod_inp_list or {}).items():
                            try:
                                mat = minp.GetAttrs()
                                mc  = mat.get("INPID_InputControl","")
                                if mc in ("SliderControl","ScrewControl","RangeControl","AngleControl"):
                                    for t, v in kf.items():
                                        try: minp[int(t)] = float(v)
                                        except Exception: pass
                                    break
                            except Exception:
                                continue
                    comp.EndUndo(True)
                    applied = bool(new_mod)
                except Exception as ex:
                    try: comp.EndUndo(False)
                    except Exception: pass
                    # Si AddModifier fallo, intentar keyframes directos como fallback
                    if kf:
                        try:
                            comp.StartUndo("MPaste: KF Fallback")
                            for t, v in kf.items():
                                try: dest_inp[int(t)] = float(v)
                                except Exception: pass
                            comp.EndUndo(True)
                            applied = True
                            return {"level":"warn","msg":f"Modifier incompatible; solo keyframes transferidos a {dest_name}.{dest_id}"}
                        except Exception:
                            try: comp.EndUndo(False)
                            except Exception: pass

            if applied:
                kf_txt = f" + {len(kf)} KF" if kf else ""
                return {"level":"ok","msg":f"Modifier transferido a {dest_name}.{dest_id}{kf_txt}"}

            return {"level":"warn","msg":f"No se pudo transferir modifier '{mod_type}'"}

        except Exception as e:
            return {"level":"error","msg":f"Error al transferir modifier: {e}"}

    # ── Ventana ────────────────────────────────────────────────────
    def minimize(self):
        try:
            if webview.windows:
                webview.windows[0].minimize()
        except Exception:
            pass

    def close(self):
        try:
            if webview.windows:
                webview.windows[0].destroy()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 7 — Lanzar ventana
# ══════════════════════════════════════════════════════════════════════════════
if not os.path.isfile(UI_FILE):
    _show_fatal(
        f"No se encontro ui.html en:\n{INSTALL_DIR}\nni en:\n{_SCRIPT_DIR}\n\n"
        "Asegurate de que main.py y ui.html esten en la misma carpeta."
    )

try:
    api    = API()
    ui_url = "file:///" + UI_FILE.replace("\\", "/")

    webview.create_window(
        title            = "MPaste",
        url              = ui_url,
        js_api           = api,
        width            = 252,
        height           = 232,   # +22px para las tabs de modo
        resizable        = False,
        frameless        = True,
        on_top           = True,
        background_color = "#0a0a0a",
        min_size         = (252, 232),
    )
    webview.start(debug=False)
except Exception as e:
    _show_fatal(
        f"No se pudo abrir la ventana.\n\nError: {e}\n\n"
        "Si el error menciona WebView2:\n  https://aka.ms/webview2\n\n"
        "Si usas Python de Microsoft Store, instala Python desde python.org."
    )
