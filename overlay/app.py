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
        log.info("Successfully loaded configuration")
    except Exception as e:
        log.exception("Failed to load config: %s", e)
        sys.exit(1)

    try:
        win = OverlayWindow(config)
        log.info("Successfully initialized OverlayWindow")
    except Exception as e:
        log.exception("Failed to create overlay window: %s", e)
        sys.exit(1)

    tray_icon = None
    try:
        icon_path = os.path.join(config.app_directory, "assets", "tray-icon.jpg")
        if not os.path.exists(icon_path):
            log.warning(f"Icon not found at {icon_path}, tray may not have an icon.")
        tray_icon = TrayIcon("Spotify Overlay", icon_path, win)
    except Exception as e:
        log.exception("Failed to create tray icon: %s", e)

    try:
        sp_client = SpotifyClient(config)
        log.info("Successfully initialized SpotifyClient")
    except Exception as e:
        log.exception("Failed to initialize Spotify client: %s", e)
        sys.exit(1)

    try:
        if tray_icon is None:
            log.info("Failed to initialize global hotkey because the Tray Icon failed to initialize")
            return

        hotkey_manager = GlobalHotkeyManager()
        log.info("Successfully initialized GlobalHotkeyManager")
    except Exception as e:
        log.exception("Failed to initialize GlobalHotkeyManager: %s", e)
        sys.exit(1)

    _ =  sp_client.now_playing_updated.connect(win.set_now_playing)  # pyright: ignore[reportAny]
    hotkey_manager.hotkey_triggered.connect(tray_icon.toggle_visibility)
    sp_client.start_polling()
    hotkey_manager.start_listener()
    log.info("Started polling using the SpotifyClient")

    # --- Improved Shutdown Logic ---
    def on_about_to_quit():
        """This function handles the actual cleanup."""
        log.info("Stopping Spotify client...")
        sp_client.stop()
        log.info("Shutdown complete.")

    _ = app.aboutToQuit.connect(on_about_to_quit)
    _ = app.aboutToQuit.connect(hotkey_manager.stop_listener)

    def signal_handler(*_args):
        """This function handles OS signals like Ctrl+C."""
        log.info("Shutdown signal received, quitting application.")
        app.quit()

    _ = signal.signal(signal.SIGINT, signal_handler)
    _ = signal.signal(signal.SIGTERM, signal_handler)

    log.info("Entering Qt main loop...")
    sys.exit(app.exec())
