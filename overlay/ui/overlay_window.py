# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAny=false, reportPossiblyUnboundVariable=false, reportUnannotatedClassAttribute=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false

import logging
import os
import io
import sys
from typing import override
import urllib.request

from PIL import Image

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QPainter, QColor, QImage, QPixmap, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar

from overlay.core.config import AppConfig
from overlay.core.state import NowPlaying

# --- Platform-specific imports and setup ---

if sys.platform.startswith("linux"):
    try:
        from Xlib import X, display  # pyright: ignore[reportUnusedImport]
        from Xlib.ext import shape

        has_xlib = True
    except ImportError:
        has_xlib = False
else:
    has_xlib = False

if sys.platform == "win32":
    try:
        import win32gui, win32con
        has_win32 = True
    except ImportError:
        has_win32 = False
else:
    has_win32 = False

def _is_wayland() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    return "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower() or bool(os.environ.get("WAYLAND_DISPLAY"))


def _truncate_text(text: str, max_length: int) -> str:
    if len(text) > max_length:
        return text[:max_length].rstrip() + "…"
    return text


def _make_window_clickthrough_x11(qt_window: QWidget):
    if not has_xlib or not qt_window.winId():
        return
    log = logging.getLogger("overlay.ui.x11")
    try:
        disp = display.Display()
        x11_window = disp.create_resource_object("window", qt_window.winId())
        x11_window.shape_select_input(shape.ShapeInput, 0, 0)
        disp.sync()
        log.info("Successfully configured click-through for X11.")
    except Exception as e:
        log.error(f"Failed to set X11 click-through properties: {e}")

def _make_window_clickthrough_windows(qt_window: QWidget):
    if not has_win32 or not qt_window.winId():
        return
    log = logging.getLogger("overlay.ui.windows")
    try:
        hwnd = int(qt_window.winId())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        new_style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        log.info("Successfully configured click-through for Windows.")
    except Exception as e:
        log.error(f"Failed to set Windows click-through properties: {e}")

class ArtLoader(QThread):
    art_loaded = Signal(QPixmap)

    def __init__(self, url: str, size: int, parent=None):  # pyright: ignore[reportMissingParameterType]
        super().__init__(parent)
        self._url, self._size = url, size
        self.log = logging.getLogger("overlay.art-loader")

    @override
    def run(self):
        try:
            req = urllib.request.Request(self._url, headers={"User-Agent": "SpotifyOverlay/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                image_data = resp.read()
            with Image.open(io.BytesIO(image_data)) as img:
                img = img.convert("RGBA")
                if self._size > 0:
                    img = img.resize((self._size, self._size), Image.Resampling.LANCZOS)
                q_image = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGBA8888)
                self.art_loaded.emit(QPixmap.fromImage(q_image))
        except Exception as e:
            self.log.error(f"Failed to load album art: {e}")


class ArtLabel(QLabel):
    def __init__(self, *args, **kwargs):  # pyright: ignore[reportMissingParameterType]
        super().__init__(*args, **kwargs)
        self.pixmap = None
        self.radius = 6

    def setPixmap(self, pixmap: QPixmap):  # pyright: ignore[reportIncompatibleMethodOverride, reportImplicitOverride]
        self.pixmap = pixmap
        self.update()

    def paintEvent(self, event):  # pyright: ignore[reportImplicitOverride, reportMissingParameterType]
        if self.pixmap:  # pyright: ignore[reportUnnecessaryComparison]
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            path = QPainterPath()
            path.addRoundedRect(self.rect(), self.radius, self.radius)

            painter.setClipPath(path)
            painter.drawPixmap(0, 0, self.pixmap)  # pyright: ignore[reportCallIssue, reportArgumentType]


class OverlayWindow(QWidget):
    def __init__(self, config: AppConfig):
        super().__init__()

        self.user_visibility_state = True
        self._is_playing = False
        self._last_np: NowPlaying | None = None
        self._progress_timer = QTimer(self)
        self._progress_ms, self._duration_ms = 0, 0
        self._config = config
        self._art_size = config.ui.art_size
        self._last_art_url: str | None = None
        self._debug = bool(os.environ.get("OVERLAY_DEBUG"))
        self._art_loader_thread: ArtLoader | None = None
        self._is_positioned = False

        self._setup_window_flags()
        self._setup_ui()
        self.log = logging.getLogger("overlay.ui.window")
        if self._config.ui.click_through:
            self._setup_click_through()
        if self._debug:
            self.show_placeholder("Waiting for Spotify…")
        else:
            self.hide()
        self.user_visibility_state = self.isVisible()

    def _setup_window_flags(self):
        self.setWindowTitle("spoverlay")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(330, 82)

    def _setup_ui(self):
        css_path = os.path.join(self._config.app_directory, "assets", "style.qss")
        if os.path.exists(css_path):
            with open(css_path, "r") as f:
                self.setStyleSheet(f.read())

        container = QWidget(self)
        container.setObjectName("container")
        container.setFixedSize(self.size())

        content_layout = QHBoxLayout(container)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(9)

        self._img = ArtLabel()
        self._img.setFixedSize(self._art_size, self._art_size)
        content_layout.addWidget(self._img)

        text_and_progress_widget = QWidget()
        text_and_progress_layout = QVBoxLayout(text_and_progress_widget)
        text_and_progress_layout.setContentsMargins(0, 0, 0, 5)
        text_and_progress_layout.setSpacing(2)

        self._title = QLabel("Title")
        self._title.setObjectName("title")
        self._artist = QLabel("Artist")
        self._artist.setObjectName("artist")

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setMaximumHeight(5)

        text_and_progress_layout.addWidget(self._title)
        text_and_progress_layout.addWidget(self._artist)
        text_and_progress_layout.addStretch()
        text_and_progress_layout.addWidget(self._progress)

        content_layout.addWidget(text_and_progress_widget)

        _ = self._progress_timer.timeout.connect(self._progress_tick)

    def _setup_click_through(self):
        self.show()

        if sys.platform == "win32":
            _make_window_clickthrough_windows(self)
        elif sys.platform.startswith("linux") and not _is_wayland():
            _make_window_clickthrough_x11(self)
        else:
            self.log.info(f"Relying on WA_TransparentForMouseEvents on {sys.platform}.")
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Hide the window again if it's not supposed to be visible initially
        if not self._debug and (self._last_np is None or not self._last_np.is_playing):
            self.hide()

    def _should_app_position_window(self) -> bool:
        if sys.platform.startswith("linux"):
            if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
                self.log.info("Hyprland detected. Deferring positioning to window manager.")
                return False
        return True

    def _position_window(self):
        screen = self.screen()
        if not screen:
            return

        geometry = screen.availableGeometry()
        win_rect = self.frameGeometry()
        margin = self._config.ui.margin

        pos = self._config.ui.position
        if pos == "top-left":
            x, y = geometry.x() + margin, geometry.y() + margin
        elif pos == "top-right":
            x, y = geometry.x() + geometry.width() - win_rect.width() - margin, geometry.y() + margin
        elif pos == "bottom-left":
            x, y = geometry.x() + margin, geometry.y() + geometry.height() - win_rect.height() - margin
        else:
            x, y = geometry.x() + geometry.width() - win_rect.width() - margin, geometry.y() + geometry.height() - win_rect.height() - margin

        self.move(x, y)
        self._is_positioned = True
        self.log.info(f"Application positioned window at ({x}, {y})")

    def showEvent(self, event):  # pyright: ignore[reportImplicitOverride, reportMissingParameterType]
        super().showEvent(event)
        if self._should_app_position_window() and not self._is_positioned:
            QTimer.singleShot(0, self._position_window)

    def paintEvent(self, event):  # pyright: ignore[reportImplicitOverride, reportMissingParameterType]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

    def show_placeholder(self, text: str):
        self._title.setText(text)
        self._artist.setText("")
        self._progress.hide()
        self._img.setPixmap(QPixmap())
        self.show()

    def is_spotify_playing(self) -> bool:
        return self._is_playing

    def get_last_now_playing(self) -> NowPlaying | None:
        return self._last_np

    @Slot(object)
    def set_now_playing(self, np: NowPlaying | None):
        self._last_np = np
        is_playing = bool(np and np.is_playing)

        if self._is_playing != is_playing:
            self._is_playing = is_playing
            if self._is_playing:
                self._start_progress_timer()
            else:
                self._stop_progress_timer()

        if not self.user_visibility_state:
            self.hide()
            return

        if self._is_playing and np:
            self._title.setText(_truncate_text(np.title or "", 30))
            self._artist.setText(_truncate_text(np.artist or "", 40))
            self._progress.show()
            self.show()

            if np.album_art_url and np.album_art_url != self._last_art_url:
                self._last_art_url = np.album_art_url
                self._load_art_async(np.album_art_url, self._art_size)
            elif not np.album_art_url:
                self._img.setPixmap(QPixmap())

            self._update_progress_from_spotify(np.progress_ms, np.duration_ms)
        else:
            self.hide()
            self._last_art_url = None

    @Slot(QPixmap)
    def _on_art_loaded(self, pixmap: QPixmap):
        self._img.setPixmap(pixmap)

    def _update_progress_from_spotify(self, progress_ms: int, duration_ms: int):
        self._progress_ms, self._duration_ms = progress_ms, duration_ms
        self._update_progress_bar()

    def _start_progress_timer(self):
        if not self._progress_timer.isActive():
            self._progress_timer.start(1000)

    def _stop_progress_timer(self):
        if self._progress_timer.isActive():
            self._progress_timer.stop()

    def _progress_tick(self):
        if not self._is_playing or self._duration_ms == 0:
            self._stop_progress_timer()
            return

        self._progress_ms += 1000
        self._update_progress_bar()

    def _update_progress_bar(self):
        if self._duration_ms > 0:
            fraction = min(self._progress_ms / self._duration_ms, 1.0)
            self._progress.setValue(int(fraction * 100))
        else:
            self._progress.setValue(0)

    def _load_art_async(self, url: str, size: int):
        if self._art_loader_thread and self._art_loader_thread.isRunning():
            self._art_loader_thread.terminate()

        self._art_loader_thread = ArtLoader(url, size, self)
        _ = self._art_loader_thread.art_loaded.connect(self._on_art_loaded)
        self._art_loader_thread.start()
