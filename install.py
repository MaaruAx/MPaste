"""
MPaste installer — python install.py
Works on Windows, macOS, Linux.
Never crashes — every error is caught, explained, and continues.

NOTE on DaVinci Resolve Free: MPaste's core operations (ImportMedia,
AppendToTimeline, ExportCurrentFrameAsStill) require resolve.GetProjectManager(),
which is only reachable via scriptapp("Resolve") — blocked in Free with no
workaround. Unlike tools that only need Fusion comp access, MPaste needs the
Project/MediaPool/Timeline API, so only the Studio (Scripts/Utility) launcher
is installed. There is no Free-compatible bridge for this tool.
"""
import subprocess, sys, os, shutil, platform, glob

HERE   = os.path.dirname(os.path.abspath(__file__))
PLAT   = platform.system()
ARCH   = platform.machine()
PY_VER = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

# ── Resolve Scripts paths per platform ───────────────────────────────────────
SCRIPTS_UTILITY = {
    "Windows": [
        os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"),
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility",
    ],
    "Darwin": [
        os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"),
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility",
    ],
    "Linux": [
        os.path.expanduser("~/.local/share/DaVinciResolve/Fusion/Scripts/Utility"),
        "/opt/resolve/Fusion/Scripts/Utility",
        "/home/resolve/Fusion/Scripts/Utility",
    ],
}

def _get_install_dir():
    """Return platform-appropriate app data dir, using platformdirs if available."""
    try:
        from platformdirs import user_data_dir
        return user_data_dir("MPaste", appauthor=False)
    except ImportError:
        pass
    if PLAT == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), "AppData", "Local"
        )
        return os.path.join(base, "MPaste")
    elif PLAT == "Darwin":
        return os.path.expanduser("~/Library/Application Support/MPaste")
    else:
        xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(xdg, "MPaste")

INSTALL_DIR = _get_install_dir()

def sep(c="-"): print(c * 54)

def log(msg, tag=""):
    prefix = f"[{tag}] " if tag else "  "
    print(f"{prefix}{msg}")

def safe(fn, *args, **kwargs):
    """Call fn, return (result, None) or (None, error_string)."""
    try:
        return fn(*args, **kwargs), None
    except Exception as e:
        return None, str(e)

# ── Detect all Python executables ─────────────────────────────────────────────
def probe_python(exe):
    try:
        r = subprocess.run(
            [exe, "-c", "import sys; print(sys.version.split()[0]); print(sys.executable)"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            lines = r.stdout.strip().splitlines()
            if len(lines) >= 2:
                ver, real_exe = lines[0], lines[1]
                maj, minor = int(ver.split(".")[0]), int(ver.split(".")[1])
                if maj == 3 and minor >= 10:
                    return real_exe, ver
    except Exception:
        pass
    return None, None

def find_all_pythons():
    seen = {}  # exe -> version

    def add(exe):
        real, ver = probe_python(exe)
        if real and real not in seen:
            seen[real] = ver

    add(sys.executable)

    if PLAT == "Windows":
        lad = os.environ.get("LOCALAPPDATA", "")
        for d in glob.glob(os.path.join(lad, "Programs", "Python", "Python3*")):
            add(os.path.join(d, "python.exe"))
        for ver in ("3.13", "3.12", "3.11", "3.10"):
            r, _ = safe(subprocess.run,
                ["py", f"-{ver}", "-c", "import sys;print(sys.executable)"],
                capture_output=True, text=True, timeout=6)
            if r and r.returncode == 0:
                add(r.stdout.strip())
        for name in ("python", "python3"):
            exe = shutil.which(name)
            if exe: add(exe)
    else:
        for name in ("python3", "python3.13", "python3.12", "python3.11", "python3.10", "python"):
            exe = shutil.which(name)
            if exe: add(exe)

    return {
        exe: ver for exe, ver in seen.items()
        if "WindowsApps" not in exe and "PythonSoftwareFoundation" not in exe
    }

def pick_best(pythons):
    def key(item):
        try: return tuple(int(x) for x in item[1].split(".")[:3])
        except Exception: return (0, 0, 0)
    return sorted(pythons.items(), key=key, reverse=True)[0] if pythons else (sys.executable, PY_VER)

# ── pip install ────────────────────────────────────────────────────────────────
def pip_install(python_exe, pkg, extra_args=None):
    cmd = [python_exe, "-m", "pip", "install", "--upgrade", pkg]
    if extra_args: cmd += extra_args
    print(f"    pip install {pkg} ...", end=" ", flush=True)
    r, err = safe(subprocess.run, cmd, capture_output=True, text=True, timeout=300)
    if err:
        print(f"ERROR ({err})"); return False
    if r.returncode == 0:
        print("OK"); return True
    errs = [l for l in r.stderr.strip().splitlines() if l.strip()]
    print(f"WARN  {errs[-1][:100] if errs else 'unknown'}")
    return False

# ── File operations ─────────────────────────────────────────────────────────────
def copy_tree(src, dst):
    """Copy src directory into dst, skipping __pycache__ and .pyc."""
    errors = []
    for item in os.listdir(src):
        if item in ("__pycache__", ".git", ".venv", "venv", "node_modules"):
            continue
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        try:
            if os.path.isdir(s):
                if os.path.exists(d): shutil.rmtree(d)
                shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(s, d)
        except Exception as e:
            errors.append(f"{item}: {e}")
    return errors

def find_scripts_dir():
    dirs = SCRIPTS_UTILITY.get(PLAT, [])
    for d in dirs:
        if os.path.isdir(d): return d
    first = dirs[0] if dirs else None
    if first:
        _, err = safe(os.makedirs, first, exist_ok=True)
        if not err: return first
    return None

def write_python_path(python_exe, location):
    try:
        path = os.path.join(location, "python_path.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(python_exe)
    except Exception as e:
        log(f"Could not write python_path.txt: {e}", "WARN")

def write_mpaste_path(install_dir, location):
    """Write mpaste_path.txt with the fully-expanded real path (no env vars)."""
    try:
        real = os.path.realpath(os.path.abspath(install_dir))
        path = os.path.join(location, "mpaste_path.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(real)
        log(f"  mpaste_path.txt -> {real}")
    except Exception as e:
        log(f"Could not write mpaste_path.txt: {e}", "WARN")

# ── CLI wrappers for Inno Setup / main.py --install-lua / --uninstall-lua ──────
# Used by the PyInstaller+Inno Setup distribution: the packaged MPaste.exe calls
# `MPaste.exe --install-lua` at install time and `--uninstall-lua` at removal.
# These just place the static MPaste.lua (which finds MPaste.exe on its own —
# see MPaste.lua's exe_path check) plus a mpaste_path.txt pointing at it.

def install_lua():
    """Copy MPaste.lua + mpaste_path.txt into Scripts/Utility. No window opened."""
    if getattr(sys, "frozen", False):
        app_dir    = os.path.dirname(sys.executable)
        bundle_dir = getattr(sys, "_MEIPASS", app_dir)
    else:
        app_dir    = HERE
        bundle_dir = HERE

    scripts_utility = find_scripts_dir()
    if not scripts_utility:
        print("[MPaste] ERROR: Scripts/Utility not found")
        return False

    # --add-data files land in _MEIPASS, not next to the exe — check both
    lua_src = os.path.join(bundle_dir, "MPaste.lua")
    if not os.path.isfile(lua_src):
        lua_src = os.path.join(app_dir, "MPaste.lua")
    if not os.path.isfile(lua_src):
        print(f"[MPaste] ERROR: MPaste.lua not found (checked {bundle_dir} and {app_dir})")
        return False

    try:
        shutil.copy2(lua_src, os.path.join(scripts_utility, "MPaste.lua"))
        # mpaste_path.txt must point to where main.py/MPaste.exe actually lives,
        # which is app_dir (exe folder), not bundle_dir (_MEIPASS, temp/internal)
        write_mpaste_path(app_dir, scripts_utility)
        print(f"[MPaste] Lua launcher installed: {scripts_utility}")
        return True
    except Exception as e:
        print(f"[MPaste] ERROR installing Lua launcher: {e}")
        return False


def uninstall_lua():
    """Remove MPaste.lua + path files from Scripts/Utility. No window opened."""
    removed = False
    for d in SCRIPTS_UTILITY.get(PLAT, []):
        for fname in ("MPaste.lua", "mpaste_path.txt", "python_path.txt"):
            p = os.path.join(d, fname)
            if os.path.isfile(p):
                try:
                    os.remove(p)
                    print(f"[MPaste] Removed {p}")
                    removed = True
                except Exception as e:
                    print(f"[MPaste] Could not remove {p}: {e}")
    return removed


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if "--install-lua" in sys.argv:
        install_lua()
        return
    if "--uninstall-lua" in sys.argv:
        uninstall_lua()
        return

    print()
    sep("=")
    print("  MPaste - Installer")
    _plat_display = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(PLAT, PLAT)
    print(f"  Platform: {_plat_display} ({ARCH})   Python: {PY_VER}")
    print(f"  Install target: {INSTALL_DIR}")
    sep("=")

    if "WindowsApps" in sys.executable or "PythonSoftwareFoundation" in sys.executable:
        print("\n  [!] Microsoft Store Python detected - cannot install packages.")
        print("      Download Python from https://www.python.org/downloads/")
        print("      and run install.py with that version.\n")
        input("Press Enter to close...")
        return

    # -- Step 1: Detect Python ----------------------------------------------
    sep()
    print("\n[1/4] Detecting Python installations...\n")
    pythons = find_all_pythons()
    if not pythons:
        print("  No Python 3.10+ found. Install from https://www.python.org")
        input("\nPress Enter to close..."); return

    python_exe, python_ver = pick_best(pythons)
    print(f"  Found {len(pythons)} installation(s):")
    for exe, ver in sorted(pythons.items(), key=lambda x: x[1], reverse=True):
        mark = " < selected" if exe == python_exe else ""
        print(f"    {ver}  {exe}{mark}")

    write_python_path(python_exe, HERE)

    # -- Step 2: Install dependencies ----------------------------------------
    sep()
    print("\n[2/4] Installing dependencies...\n")

    r, _ = safe(subprocess.run,
        [python_exe, "-c", "import PySide6.QtWebEngineWidgets; print('ok')"],
        capture_output=True, text=True, timeout=15)
    if r and "ok" in r.stdout:
        print("    PySide6 already installed  OK")
    else:
        pip_install(python_exe, "PySide6")
        r2, _ = safe(subprocess.run,
            [python_exe, "-c", "import PySide6.QtWebEngineWidgets"],
            capture_output=True, text=True, timeout=15)
        if r2 and r2.returncode != 0:
            log("QtWebEngineWidgets not found - trying PySide6[WebEngine]", "WARN")
            pip_install(python_exe, "PySide6[WebEngine]")

    r3, _ = safe(subprocess.run,
        [python_exe, "-c", "import PIL; print('ok')"],
        capture_output=True, text=True, timeout=15)
    if r3 and "ok" in r3.stdout:
        print("    Pillow already installed  OK")
    else:
        pip_install(python_exe, "Pillow")

    if PLAT == "Windows":
        r4, _ = safe(subprocess.run,
            [python_exe, "-c", "import win32clipboard; print('ok')"],
            capture_output=True, text=True, timeout=15)
        if r4 and "ok" in r4.stdout:
            print("    pywin32 already installed  OK")
        else:
            pip_install(python_exe, "pywin32")

    r5, _ = safe(subprocess.run,
        [python_exe, "-c", "import platformdirs"],
        capture_output=True, text=True, timeout=8)
    if r5 and r5.returncode == 0:
        print("    platformdirs already installed  OK")
    else:
        pip_install(python_exe, "platformdirs")

    # -- Step 3: Copy MPaste to install dir ----------------------------------
    sep()
    print(f"\n[3/4] Installing MPaste to: {INSTALL_DIR}\n")
    _, err = safe(os.makedirs, INSTALL_DIR, exist_ok=True)
    if err:
        log(f"Cannot create install dir: {err}", "ERR")
        log("Falling back to current directory", "WARN")
        install_dir = HERE
    else:
        install_dir = INSTALL_DIR

    KEEP_PATTERNS = {"settings.json", "images", "mpaste_path.txt", "python_path.txt"}
    if os.path.isdir(install_dir) and install_dir != HERE:
        for item in os.listdir(install_dir):
            if item in KEEP_PATTERNS or item.startswith("."):
                continue
            target = os.path.join(install_dir, item)
            src_equiv = os.path.join(HERE, item)
            if not os.path.exists(src_equiv):
                try:
                    if os.path.isdir(target): shutil.rmtree(target)
                    else: os.remove(target)
                    log(f"  Removed stale: {item}")
                except Exception as e:
                    log(f"  Could not remove {item}: {e}", "WARN")

    _here_real = os.path.realpath(os.path.abspath(HERE))
    _inst_real = os.path.realpath(os.path.abspath(install_dir))
    if _here_real == _inst_real:
        log("Source == install dir — skipping file copy (already in place)")
    else:
        errs = copy_tree(HERE, install_dir)
        if errs:
            for e in errs: log(e, "WARN")
        else:
            log(f"OK - copied to {install_dir}")

    write_python_path(python_exe, install_dir)
    write_mpaste_path(install_dir, install_dir)

    # -- Step 4: Install Resolve launcher (Studio only — see module docstring)
    sep()
    print("\n[4/4] Installing Resolve launcher...\n")

    scripts_utility = find_scripts_dir()
    if scripts_utility:
        log(f"Studio launcher (Scripts/Utility): {scripts_utility}")
        for fname in ("MPaste.lua", "python_path.txt"):
            src = os.path.join(install_dir, fname)
            if not os.path.isfile(src): src = os.path.join(HERE, fname)
            if os.path.isfile(src):
                _, err = safe(shutil.copy2, src, os.path.join(scripts_utility, fname))
                if err: log(f"  Cannot copy {fname}: {err}", "WARN")
                else:   log(f"  OK  {fname}")
        write_mpaste_path(install_dir, scripts_utility)
    else:
        log("Scripts/Utility not found - copy MPaste.lua manually", "WARN")
        for d in SCRIPTS_UTILITY.get(PLAT, []):
            log(f"  {d}", "")

    # -- Summary ----------------------------------------------------------------
    sep("=")
    print(f"\n  Python:   {python_exe}")
    print(f"  MPaste:   {install_dir}")
    print()
    print("  Open Resolve: Workspace > Scripts > MPaste")
    print()
    print("  NOTE: DaVinci Resolve Free is not supported. MPaste needs the")
    print("  Project/MediaPool/Timeline API, which Free blocks entirely —")
    print("  this is a Blackmagic restriction, not a bug in MPaste.")
    print()
    print("  Run standalone:  python main.py")
    print()
    sep("=")
    input("Press Enter to close...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        import traceback
        print(f"\n[FATAL] Unexpected error: {e}")
        traceback.print_exc()
        input("\nPress Enter to close...")
