# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false

import logging
import os
import signal
import sys

from PySide6.QtWidgets import QApplication

from overlay.core.config import load_config
from overlay.core.spotify_client import SpotifyClient
from overlay.core.hotkey_manager import GlobalHotkeyManager
from overlay.ui.overlay_window import OverlayWindow
from overlay.ui.tray_icon import TrayIcon


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
        log.info("Configuration from .env and Environment Variables has been loaded.")
    except Exception as e:
        log.exception("Failed to load configuration: %s", e)
        sys.exit(1)

    try:
        win = OverlayWindow(config)
        log.info("Overlay window has been created.")
    except Exception as e:
        log.exception("Failed to create overlay window: %s", e)
        sys.exit(1)

    tray_icon = None
    try:
        icon_path = os.path.join(config.app_directory, "assets", "tray-icon.jpg")
        if not os.path.exists(icon_path):
            log.warning(f"Icon not found at {icon_path}, tray may not have an icon.")
        tray_icon = TrayIcon("Spotify Overlay", icon_path, win)
        log.info("System tray icon Successfully created.")
    except Exception as e:
        log.exception("Failed to create the tray icon: %s", e)

    try:
        sp_client = SpotifyClient(config)
        log.info("Spotify client connected Successfully.")
    except Exception as e:
        log.exception("Failed to initialize the spotify client: %s", e)
        sys.exit(1)

    try:
        if tray_icon is None:
            log.warning("Failed to add the global hotkey because the Tray Icon failed to initialize.")
            return

        hotkey_manager = GlobalHotkeyManager()
        log.info("Global hotkey has been configured.")
    except Exception as e:
        log.exception("Failed to initialize GlobalHotkeyManager: %s", e)
        sys.exit(1)

    _ = sp_client.now_playing_updated.connect(win.set_now_playing)
    _ = hotkey_manager.hotkey_triggered.connect(tray_icon.toggle_visibility)
    log.info("Listening for now_playing and toggle_visibility events.")

    sp_client.start_polling()
    log.info("Started polling using the the spotify client")

    hotkey_manager.start_listener()
    log.info("Started the hotkey listener.")

    def on_about_to_quit():
        log.info("Stopping the spotify client...")
        sp_client.stop()
        log.info("Stopped the spotify client...")

        log.info("Stopping the hotkey listener...")
        hotkey_manager.stop_listener()
        log.info("Stopped the hotkey listener...")

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
