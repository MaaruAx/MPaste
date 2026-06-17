"""
settings_window.py — MPaste
Ventana de ajustes con QWebEngineView + settings.html.
Mismo renderer, mismas fuentes, mismo look que la ventana principal.
"""

import json
from pathlib import Path

from PySide6.QtCore           import Qt, QObject, Slot, Signal, QFile, QIODevice
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore  import QWebEngineScript, QWebEngineSettings
from PySide6.QtWebChannel     import QWebChannel
from PySide6.QtWidgets        import QMainWindow, QApplication
from PySide6.QtCore           import QUrl


# ── Backend exclusivo de la ventana de ajustes ───────────────────────────────
class _SettingsBackend(QObject):
    def __init__(self, win: "SettingsWindow"):
        super().__init__()
        self._win = win

    @Slot(result=str)
    def get_settings(self) -> str:
        return json.dumps(self._win._cfg)

    @Slot(str)
    def save_and_close(self, data_json: str):
        try:
            new_cfg = json.loads(data_json)
            self._win.settings_saved.emit(new_cfg)
            self._win.close()
        except Exception:
            pass

    @Slot()
    def start_move(self):
        try:
            h = self._win.windowHandle()
            if h:
                h.startSystemMove()
        except Exception:
            pass

    @Slot()
    def close_window(self):
        self._win.close()


# ── Ventana ───────────────────────────────────────────────────────────────────
class SettingsWindow(QMainWindow):
    settings_saved = Signal(dict)

    def __init__(self, cfg: dict,
                 settings_html: Path,
                 parent=None):
        super().__init__(parent,
                         Qt.WindowType.Window |
                         Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle("MPaste — Ajustes")
        self.setFixedSize(300, 480)

        self._cfg          = dict(cfg)
        self._settings_html = settings_html

        # WebEngine
        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        # Ajustes del motor
        ws = self._view.page().settings()
        ws.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        ws.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # QWebChannel
        self._channel = QWebChannel()
        self._backend = _SettingsBackend(self)
        self._channel.registerObject("backend", self._backend)
        self._view.page().setWebChannel(self._channel)

        # Inject qwebchannel.js via setSourceCode (reliable for file:// in Qt 6)
        f = QFile(":/qtwebchannel/qwebchannel.js")
        if f.open(QIODevice.OpenModeFlag.ReadOnly):
            content = bytes(f.readAll()).decode("utf-8")
            f.close()
            s = QWebEngineScript()
            s.setName("settings-qwebchannel")
            s.setSourceCode(content)
            s.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            s.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            self._view.page().scripts().insert(s)
        else:
            print("[MPaste] WARNING: qrc:/qtwebchannel/qwebchannel.js not found")

        # Cargar HTML
        if self._settings_html.is_file():
            self._view.setUrl(QUrl.fromLocalFile(str(self._settings_html)))
        else:
            self._view.setHtml(
                f"<body style='background:#0a0a0a;color:#e05c5c;"
                f"font-family:monospace;padding:24px'>"
                f"<b>settings.html no encontrado</b><p>{self._settings_html}</p></body>"
            )

    def show_near(self, anchor: QMainWindow):
        ag  = anchor.frameGeometry()
        scr = QApplication.primaryScreen().availableGeometry()
        x   = ag.right() + 8
        if x + self.width() > scr.right():
            x = ag.left() - self.width() - 8
        x = max(scr.left(), x)
        y = max(scr.top(), min(ag.top(), scr.bottom() - self.height()))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
