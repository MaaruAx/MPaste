-- MPaste launcher
-- Place in: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
-- In Resolve (any page): Workspace > Scripts > MPaste

local is_win = (package.config:sub(1,1) == "\\")
local sep    = is_win and "\\" or "/"

-- Resolve script's own directory
local script_dir = (debug.getinfo(1,"S").source or ""):match("^@(.+)[/\\][^/\\]+$") or ""

-- Default install paths
local function default_mpaste_dir()
    if is_win then
        local la = os.getenv("LOCALAPPDATA") or ""
        if la ~= "" then return la .. "\\MPaste" end
        local up = os.getenv("USERPROFILE") or os.getenv("HOME") or "C:\\Users\\Default"
        return up .. "\\AppData\\Local\\MPaste"
    else
        local home = os.getenv("HOME") or "/tmp"
        local mac_test = io.open(home .. "/Library", "r")
        if mac_test then mac_test:close(); return home .. "/Library/Application Support/MPaste"
        else return home .. "/.local/share/MPaste" end
    end
end

-- Read mpaste_path.txt if present (next to this script, or in default install dir)
local mpaste_dir = default_mpaste_dir()
local txt_paths = {
    script_dir  .. sep .. "mpaste_path.txt",
    mpaste_dir  .. sep .. "mpaste_path.txt",
}
for _, tp in ipairs(txt_paths) do
    local f = io.open(tp, "r")
    if f then
        local p = f:read("*l"); f:close()
        if p and p ~= "" then mpaste_dir = p; break end
    end
end

local main_py = mpaste_dir .. sep .. "main.py"

-- Verify main.py exists
local check = io.open(main_py, "r")
if not check then
    print("[MPaste] ERROR: main.py not found at: " .. main_py ..
          "\nRun install.py first, or edit mpaste_path.txt at:\n" ..
          (script_dir ~= "" and (script_dir .. sep .. "mpaste_path.txt") or "(script dir unknown)"))
    return
end
check:close()

-- Find Python
local python_exe = nil

-- 1. python_path.txt written by install.py
local py_txt_paths = {
    script_dir .. sep .. "python_path.txt",
    mpaste_dir .. sep .. "python_path.txt",
}
for _, pp in ipairs(py_txt_paths) do
    local f = io.open(pp, "r")
    if f then
        local p = f:read("*l"); f:close()
        if p and p ~= "" then
            local tf = io.open(p, "r")
            if tf then tf:close(); python_exe = p; break end
        end
    end
end

-- 2. Common Windows paths fallback
if not python_exe and is_win then
    local la = os.getenv("LOCALAPPDATA") or ""
    local candidates = {
        la .. "\\Programs\\Python\\Python312\\python.exe",
        la .. "\\Programs\\Python\\Python311\\python.exe",
        la .. "\\Programs\\Python\\Python310\\python.exe",
        la .. "\\Programs\\Python\\Python39\\python.exe",
    }
    for _, c in ipairs(candidates) do
        local tf = io.open(c, "r")
        if tf then tf:close(); python_exe = c; break end
    end
end

-- 3. Last resort: rely on PATH
if not python_exe then
    python_exe = is_win and "python" or "python3"
end

-- ── Launch ───────────────────────────────────────────────────────────────────
-- Prefer a packaged MPaste.exe next to main.py if it exists (PyInstaller build)
local exe_path = mpaste_dir .. sep .. "MPaste.exe"
local exe_check = is_win and io.open(exe_path, "r") or nil
local cmd

if exe_check then
    exe_check:close()
    cmd = string.format('start "" /B "%s"', exe_path)
else
    if is_win then
        -- Use pythonw.exe if available (no console window)
        local pyw = python_exe:gsub("python%.exe$", "pythonw.exe")
        local tf2 = io.open(pyw, "r")
        if tf2 then tf2:close(); python_exe = pyw end
        cmd = string.format('start "" /B "%s" "%s"', python_exe, main_py)
    else
        cmd = string.format('"%s" "%s" > /tmp/mpaste.log 2>&1 &', python_exe, main_py)
    end
end

print("[MPaste] Launching: " .. cmd)
os.execute(cmd)
