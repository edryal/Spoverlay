# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false

import logging
import os
import signal
import sys
from typing import final

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from overlay.core.config import load_config, save_config, APP_NAME
from overlay.core.models import AppConfig
from overlay.core.spotify_client import SpotifyClient
from overlay.core.hotkey_manager import GlobalHotkeyManager
from overlay.core.ipc_listener import IpcListener
from overlay.ui.overlay_window import OverlayWindow
from overlay.ui.tray_icon import TrayIcon


APP_DISPLAY_NAME = "Spoverlay"
IPC_SOCKET_PATH = f"/tmp/{APP_NAME}.sock"
TRAY_ICON_PATH = os.path.join("assets", "tray-icon.jpg")

log = logging.getLogger(__name__)


@final
class SpoverlayApp(QObject):
    """
    Manages the lifecycle of the entire Spoverlay application and its components.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = self._load_initial_config()
        
        self.overlay_window = OverlayWindow(self.config)
        self.spotify_client = SpotifyClient(self.config)
        
        icon_path = os.path.join(self.config.app_directory, TRAY_ICON_PATH)
        if not os.path.exists(icon_path):
            log.warning(f"Icon not found at {icon_path}, tray may not have an icon.")
            
        self.tray_icon = TrayIcon(APP_DISPLAY_NAME, icon_path, self.overlay_window, self.spotify_client, self.config)
        
        # These will be initialized based on the platform
        self.hotkey_manager = None
        self.ipc_listener = None

        self._setup_platform_integrations()
        self._connect_signals()
        self._setup_shutdown_hooks()
        
    def _load_initial_config(self) -> AppConfig:
        try:
            log.info("Loading overlay configuration...")

            config = load_config()
            log.info("Overlay configuration loaded.")

            return config
        except Exception:
            log.exception("Fatal error: Failed to load configuration.")
            sys.exit(1)

    def _setup_platform_integrations(self):
        """Sets up the global hotkey or IPC listener based on the OS."""
        if sys.platform == "linux":
            log.info("Setting up IPC listener for Linux.")

            self.ipc_listener = IpcListener(IPC_SOCKET_PATH)
            _ = self.ipc_listener.toggle_visibility_requested.connect(self.tray_icon.toggle_visibility)
            self.ipc_listener.start()
        else:
            log.info(f"Setting up global hotkey for {sys.platform}.")
            try:
                self.hotkey_manager = GlobalHotkeyManager()
                _ = self.hotkey_manager.hotkey_triggered.connect(self.tray_icon.toggle_visibility)
                self.hotkey_manager.start_listener()

                log.info("Global hotkey listener started.")
            except Exception:
                log.exception("Fatal error: Failed to initialize GlobalHotkeyManager.")
                sys.exit(1)

    def _connect_signals(self):
        """Connects all the application's internal signals and slots."""

        _ = self.tray_icon.configure_window.config_saved.connect(self._on_config_changed)
        _ = self.spotify_client.clear_ui_requested.connect(self.overlay_window.clear_ui)
        _ = self.spotify_client.now_playing_updated.connect(self.overlay_window.set_now_playing)

        log.info("Application signals connected.")

    def _setup_shutdown_hooks(self):
        """Sets up handlers for graceful application shutdown."""

        QApplication.instance().aboutToQuit.connect(self._on_about_to_quit)  # pyright: ignore[reportUnusedCallResult, reportOptionalMemberAccess]
        _ = signal.signal(signal.SIGINT, self._on_os_signal)
        _ = signal.signal(signal.SIGTERM, self._on_os_signal)

        log.info("Shutdown hooks registered.")
        
    def run(self):
        """Starts the application's main processes."""

        log.info("Performing initial Spotify state fetch...")
        self.spotify_client.initial_fetch_and_emit()

        log.info("Starting continuous Spotify polling...")
        self.spotify_client.start_polling()

    def _on_config_changed(self, new_config: AppConfig):
        """Handles the 'hot reload' of the configuration."""

        log.info("Configuration changed, applying new settings...")
        self.config = new_config
        save_config(self.config)

        self.overlay_window.on_config_changed(self.config)
        self.spotify_client.on_config_changed(self.config)

        log.info("Settings applied and saved successfully.")

    def _on_about_to_quit(self):
        """Cleans up all resources before the application exits."""

        log.info("Shutdown sequence initiated...")
        self.spotify_client.stop()

        if self.hotkey_manager:
            self.hotkey_manager.stop_listener()

        if self.ipc_listener:
            self.ipc_listener.stop()

        log.info("All components stopped. Shutdown complete.")

    def _on_os_signal(self, *_args):
        """Handles OS signals like Ctrl+C for a graceful exit."""

        log.info("OS shutdown signal received, quitting application.")
        QApplication.instance().quit()  # pyright: ignore[reportOptionalMemberAccess]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log.info(f"--- Starting {APP_DISPLAY_NAME} ---")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)

    spoverlay_app = SpoverlayApp()
    spoverlay_app.run()

    log.info("Entering Qt main event loop...")
    sys.exit(app.exec())
