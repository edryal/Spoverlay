# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false

import logging
import os
import signal
import sys
import socket
from threading import Thread
from typing import final

from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QApplication

from overlay.core.config import load_config, save_config
from overlay.core.models import AppConfig
from overlay.core.spotify_client import SpotifyClient
from overlay.core.hotkey_manager import GlobalHotkeyManager
from overlay.ui.overlay_window import OverlayWindow
from overlay.ui.tray_icon import TrayIcon


@final
class IpcListener(QObject):
    toggle_visibility_requested = Signal()

    def __init__(self, socket_path, parent=None):
        super().__init__(parent)
        self.log = logging.getLogger("overlay.ipc")
        self.socket_path = socket_path
        self._running = False
        self._thread = Thread(target=self.run, daemon=True)

        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(self.socket_path)
        except (FileNotFoundError, ConnectionRefusedError):
            pass
        self.log.info("IPC listener stopping.")

    def run(self):
        self.log.info(f"IPC listener starting at {self.socket_path}")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            server.bind(self.socket_path)
            server.listen(1)

            # Timeout to periodically check if we should stop running
            server.settimeout(1.0)

            while self._running:
                try:
                    # This needs to be tuple or else the IPC won't work
                    connection, _ = server.accept()  # pyright: ignore[reportAny]
                    connection.close()
                    self.log.info("IPC signal received, requesting visibility toggle.")
                    self.toggle_visibility_requested.emit()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        self.log.error(f"Error in IPC listener: {e}")
        finally:
            server.close()
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
            self.log.info("IPC listener has shut down.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("overlay.app")
    log.info("Starting spotify overlay app...")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("spoverlay")
    app.setApplicationDisplayName("spoverlay")

    try:
        config = load_config()
        log.info("Overlay configuration has been loaded.")
    except Exception as e:
        log.exception("Failed to load configuration: %s", e)
        sys.exit(1)

    try:
        win = OverlayWindow(config)
        log.info("Overlay window has been created.")
    except Exception as e:
        log.exception("Failed to create overlay window: %s", e)
        sys.exit(1)

    spotify_client = None
    try:
        spotify_client = SpotifyClient(config)
        log.info("Spotify client connected Successfully.")
    except Exception as e:
        log.exception("Failed to initialize the spotify client: %s", e)
        sys.exit(1)

    tray_icon = None
    try:
        icon_path = os.path.join(config.app_directory, "assets", "tray-icon.jpg")
        if not os.path.exists(icon_path):
            log.warning(f"Icon not found at {icon_path}, tray may not have an icon.")
        tray_icon = TrayIcon("Spotify Overlay", icon_path, win, spotify_client, config)
        log.info("System tray icon Successfully created.")
    except Exception as e:
        log.exception("Failed to create the tray icon: %s", e)

    hotkey_manager = None
    ipc_listener = None

    if tray_icon:
        if sys.platform == "linux":
            log.info("Setting up IPC listener for Wayland/Hyprland.")
            socket_path = "/tmp/spoverlay.sock"
            ipc_listener = IpcListener(socket_path)
            _ = ipc_listener.toggle_visibility_requested.connect(tray_icon.toggle_visibility)
            ipc_listener.start()
        else:
            log.info(f"Setting up global hotkey for non-Linux platform: {sys.platform}.")
            try:
                hotkey_manager = GlobalHotkeyManager()
                _ = hotkey_manager.hotkey_triggered.connect(tray_icon.toggle_visibility)
                hotkey_manager.start_listener()
                log.info("Started the pynput hotkey listener.")
            except Exception as e:
                log.exception("Failed to initialize GlobalHotkeyManager: %s", e)
                sys.exit(1)
    else:
        log.warning("Tray Icon failed to initialize. Hotkey setup will be skipped.")

    def on_config_changed(new_config_values: AppConfig):
        log.info("Configuration changed, applying settings...")
        
        # Update the shared config object in-place
        config.ui = new_config_values.ui
        config.poll_interval_ms = new_config_values.poll_interval_ms
        
        save_config(config)
        win.on_config_changed(config)
        spotify_client.on_config_changed(config)
        log.info("Settings applied and saved.")

    if tray_icon:
        _ = tray_icon.configure_window.config_saved.connect(on_config_changed)

    _ = spotify_client.clear_ui_requested.connect(win.clear_ui)
    _ = spotify_client.now_playing_updated.connect(win.set_now_playing)
    log.info("Listening for now_playing events.")

    spotify_client.initial_fetch_and_emit()
    spotify_client.start_polling()
    log.info("Started polling using the the spotify client")

    def on_about_to_quit():
        log.info("Stopping the spotify client...")
        spotify_client.stop()
        log.info("Stopped the spotify client...")

        if hotkey_manager:
            log.info("Stopping the hotkey listener...")
            hotkey_manager.stop_listener()
            log.info("Stopped the hotkey listener...")

        if ipc_listener:
            log.info("Stopping the IPC listener...")
            ipc_listener.stop()
            log.info("Stopped the IPC listener...")

        log.info("Shutdown complete.")

    _ = app.aboutToQuit.connect(on_about_to_quit)

    def signal_handler(*_args):
        """This function handles OS signals like Ctrl+C."""
        log.info("Shutdown signal received, quitting application.")
        app.quit()

    _ = signal.signal(signal.SIGINT, signal_handler)
    _ = signal.signal(signal.SIGTERM, signal_handler)
    log.info("Listening for SIGINT and SIGTERM signals.")

    log.info("Entering Qt main loop...")
    sys.exit(app.exec())
