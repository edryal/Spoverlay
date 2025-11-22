# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAny=false, reportPossiblyUnboundVariable=false, reportUnannotatedClassAttribute=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false

import io
import logging
import os
import sys
from typing import override
import urllib.request

from PIL import Image
from PySide6.QtCore import QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from overlay.core.models import AppConfig, NowPlaying


WINDOW_WIDTH = 330
WINDOW_HEIGHT = 82
TITLE_MAX_LEN = 30
ARTIST_MAX_LEN = 40
PROGRESS_BAR_HEIGHT = 5
ART_IMAGE_CORNER_RADIUS = 6
USER_AGENT = "Spoverlay/1.0"

log = logging.getLogger(__name__)


has_win32 = False
if sys.platform == "win32":
    try:
        import win32gui, win32con  # pyright: ignore[reportMissingModuleSource]

        has_win32 = True
    except ImportError:
        log.warning("pywin32 not found. Windows click-through will not work.")


def _make_window_clickthrough_windows(qt_window: QWidget):
    """Configures click-through on Windows using pywin32."""

    if not has_win32 or not qt_window.winId():
        return
    try:
        hwnd = int(qt_window.winId())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        new_style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        log.info("Successfully configured click-through for Windows.")
    except Exception as e:
        log.error(f"Failed to set Windows click-through properties: {e}")


def _truncate_text(text: str, max_length: int) -> str:
    """Truncates text with an ellipsis if it exceeds the max length."""
    return text[:max_length].rstrip() + "…" if len(text) > max_length else text


class ArtLoader(QThread):
    """A background thread to download and process album art without freezing the UI."""

    art_loaded = Signal(QPixmap)

    def __init__(self, url: str, size: int):
        super().__init__()
        self._url, self._size = url, size

    @override
    def run(self):
        try:
            req = urllib.request.Request(self._url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                image_data = resp.read()
            with Image.open(io.BytesIO(image_data)) as img:
                img = img.convert("RGBA")
                if self._size > 0:
                    img = img.resize((self._size, self._size), Image.Resampling.LANCZOS)
                q_image = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGBA8888)
                self.art_loaded.emit(QPixmap.fromImage(q_image))
        except Exception as e:
            log.error(f"Failed to load album art from {self._url}: {e}")


class ArtLabel(QLabel):
    """A custom QLabel that paints its pixmap with rounded corners."""

    def __init__(self, *args, **kwargs):  # pyright: ignore[reportMissingParameterType]
        super().__init__(*args, **kwargs)
        self._pixmap: QPixmap | None = None
        self.radius = ART_IMAGE_CORNER_RADIUS

    @override
    def setPixmap(self, pixmap: QPixmap | None):  # pyright: ignore[reportIncompatibleMethodOverride]
        self._pixmap = pixmap
        self.update()

    @override
    def paintEvent(self, event):  # pyright: ignore[reportMissingParameterType, reportIncompatibleMethodOverride]
        if self._pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(self.rect(), self.radius, self.radius)
            painter.setClipPath(path)
            painter.drawPixmap(self.rect(), self._pixmap)


class OverlayWindow(QWidget):
    """
    The main overlay window. It displays the currently playing track information,
    handles its own positioning, and updates its appearance based on config changes.
    """

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config

        self.user_visibility_state = True
        self._is_playing = False
        self._last_np: NowPlaying | None = None
        self._last_art_url: str | None = None
        self._art_loader_thread: ArtLoader | None = None
        self._is_positioned = False

        self._title_label: QLabel
        self._artist_label: QLabel
        self._art_label: ArtLabel
        self._progress_bar: QProgressBar
        self._progress_timer = QTimer(self)
        self._progress_ms = 0
        self._duration_ms = 0

        self._setup_window_properties()
        self._create_widgets()
        self._layout_widgets()
        self._connect_signals()

        if self._config.ui.click_through:
            self._setup_click_through()

        self.show_placeholder("Connecting to Spotify…")
        self.user_visibility_state = self.isVisible()

    def _setup_window_properties(self):
        """Sets the window flags, attributes, and size."""

        self.setWindowTitle("spoverlay")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        css_path = os.path.join(self._config.app_directory, "assets", "style.qss")
        if os.path.exists(css_path):
            with open(css_path, "r") as f:
                self.setStyleSheet(f.read())
        else:
            log.warning(f"Stylesheet not found at {css_path}")

    def _create_widgets(self):
        """Initializes all the child widgets for the overlay."""

        self._art_label = ArtLabel()
        self._art_label.setFixedSize(self._config.ui.art_size, self._config.ui.art_size)

        self._title_label = QLabel("Title")
        self._title_label.setObjectName("title")

        self._artist_label = QLabel("Artist")
        self._artist_label.setObjectName("artist")

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setMaximumHeight(PROGRESS_BAR_HEIGHT)

    def _layout_widgets(self):
        """Arranges the created widgets using layouts."""
        container = QWidget(self)
        container.setObjectName("container")
        container.setFixedSize(self.size())

        content_layout = QHBoxLayout(container)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(9)
        content_layout.addWidget(self._art_label)

        text_and_progress_layout = QVBoxLayout()
        text_and_progress_layout.setContentsMargins(0, 0, 0, 5)
        text_and_progress_layout.setSpacing(2)
        text_and_progress_layout.addWidget(self._title_label)
        text_and_progress_layout.addWidget(self._artist_label)
        text_and_progress_layout.addStretch()
        text_and_progress_layout.addWidget(self._progress_bar)

        content_layout.addLayout(text_and_progress_layout)

    def _connect_signals(self):
        """Connects internal signals, like the progress timer."""

        _ = self._progress_timer.timeout.connect(self._progress_tick)

    @Slot()
    def clear_ui(self):
        """Clears the overlay content, showing a placeholder for re-authentication."""

        log.info("Clearing UI for re-authentication.")
        self.show_placeholder("Re-authenticating...")
        self._last_np = None
        self._last_art_url = None
        self._is_playing = False
        self._stop_progress_timer()

    def _setup_click_through(self):
        """Enables click-through based on the operating system."""

        if sys.platform == "win32":
            _make_window_clickthrough_windows(self)
        else:
            log.info(f"Relying on WA_TransparentForMouseEvents for click-through on {sys.platform}.")
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def _should_app_position_window(self) -> bool:
        """Determines if the application should control window position."""

        # On Hyprland, let the compositor handle positioning via window rules.
        if sys.platform.startswith("linux") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            log.info("Hyprland detected. Deferring positioning to window manager.")
            return False
        return True

    def _position_window(self):
        """Calculates and sets the window's position based on config."""

        screen = self.screen()
        if not screen:
            return

        geometry = screen.availableGeometry()
        win_rect = self.frameGeometry()
        margin = self._config.ui.margin
        pos = self._config.ui.position

        x, y = 0, 0
        if pos == "top-left":
            x, y = geometry.x() + margin, geometry.y() + margin
        elif pos == "top-right":
            x, y = geometry.x() + geometry.width() - win_rect.width() - margin, geometry.y() + margin
        elif pos == "bottom-left":
            x, y = geometry.x() + margin, geometry.y() + geometry.height() - win_rect.height() - margin
        else:  # bottom-right
            x, y = geometry.x() + geometry.width() - win_rect.width() - margin, geometry.y() + geometry.height() - win_rect.height() - margin

        self.move(x, y)
        self._is_positioned = True
        log.info(f"Application positioned window at ({x}, {y}) for position '{pos}'.")

    @override
    def showEvent(self, event):  # pyright: ignore[reportMissingParameterType]
        """Overrides QWidget.showEvent to position the window on first show."""

        super().showEvent(event)
        if self._should_app_position_window() and not self._is_positioned:
            QTimer.singleShot(0, self._position_window)

    @override
    def paintEvent(self, event):  # pyright: ignore[reportMissingParameterType]
        """Overrides QWidget.paintEvent to ensure a transparent background."""

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

    def show_placeholder(self, text: str):
        """Displays a simple text message in the overlay."""

        self._title_label.setText(text)
        self._artist_label.setText("")
        self._progress_bar.hide()
        self._art_label.setPixmap(None)
        self.show()

    def get_last_now_playing(self) -> NowPlaying | None:
        """Returns the last known 'NowPlaying' state."""

        return self._last_np

    @Slot(object)  # pyright: ignore[reportArgumentType]
    def set_now_playing(self, np: NowPlaying | None):
        """The main slot that receives updates from the SpotifyClient."""

        self._last_np = np
        is_now_playing = bool(np and np.is_playing)

        # Start/stop the local progress timer based on playback state changes.
        if self._is_playing != is_now_playing:
            self._is_playing = is_now_playing
            if self._is_playing:
                self._start_progress_timer()
            else:
                self._stop_progress_timer()

        # Respect the user's choice to hide the overlay.
        if not self.user_visibility_state:
            self.hide()
            return

        if self._is_playing and np:
            # Update UI elements with the new track data.
            self._title_label.setText(_truncate_text(np.title or "", TITLE_MAX_LEN))
            self._artist_label.setText(_truncate_text(np.artist or "", ARTIST_MAX_LEN))
            self._progress_bar.show()
            self._update_progress_from_spotify(np.progress_ms, np.duration_ms)

            # Fetch new album art only if the URL has changed.
            if np.album_art_url and np.album_art_url != self._last_art_url:
                self._last_art_url = np.album_art_url
                self._load_art_async(np.album_art_url)
            elif not np.album_art_url:
                self._art_label.setPixmap(None)

            self.show()
        else:
            # If nothing is playing, hide the overlay.
            self.hide()
            self._last_art_url = None

    @Slot(QPixmap)
    def _on_art_loaded(self, pixmap: QPixmap):
        """Slot to receive the loaded album art from the background thread."""

        self._art_label.setPixmap(pixmap)

    def _update_progress_from_spotify(self, progress_ms: int, duration_ms: int):
        """Resets the local progress based on data from Spotify."""

        self._progress_ms, self._duration_ms = progress_ms, duration_ms
        self._update_progress_bar()

    def _start_progress_timer(self):
        if not self._progress_timer.isActive():
            self._progress_timer.start(1000)

    def _stop_progress_timer(self):
        if self._progress_timer.isActive():
            self._progress_timer.stop()

    def _progress_tick(self):
        """Advances the progress bar every second."""

        if not self._is_playing or self._duration_ms == 0:
            return

        self._progress_ms += 1000
        self._update_progress_bar()

    def _update_progress_bar(self):
        """Calculates and sets the progress bar's value (0-100)."""

        if self._duration_ms > 0:
            fraction = min(self._progress_ms / self._duration_ms, 1.0)
            self._progress_bar.setValue(int(fraction * 100))
        else:
            self._progress_bar.setValue(0)

    def _load_art_async(self, url: str):
        """Starts a background thread to download album art."""

        # Terminate any previous loader to prevent a race condition.
        if self._art_loader_thread and self._art_loader_thread.isRunning():
            self._art_loader_thread.terminate()

        self._art_loader_thread = ArtLoader(url, self._config.ui.art_size)
        _ = self._art_loader_thread.art_loaded.connect(self._on_art_loaded)
        self._art_loader_thread.start()

    def on_config_changed(self, new_config: AppConfig):
        """Applies new configuration settings to the overlay window (hot-reload)."""

        log.info("Applying new UI configuration...")
        self._config = new_config

        # Resize art label and re-download art if size changed.
        art_size_changed = self._art_label.width() != new_config.ui.art_size
        self._art_label.setFixedSize(new_config.ui.art_size, new_config.ui.art_size)
        if art_size_changed and self._last_art_url:
            self._load_art_async(self._last_art_url)

        # Re-evaluate click-through settings.
        self._setup_click_through()

        # Force a repositioning of the window with the new settings.
        self._is_positioned = False
        if self.isVisible():
            self._position_window()
