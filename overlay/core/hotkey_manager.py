import logging
from threading import Thread
from typing import final

from PySide6.QtCore import QObject, Signal
from pynput import keyboard

from overlay.core.models import AppConfig


DEFAULT_HOTKEY = "F7"

log = logging.getLogger(__name__)


@final
class HotkeyManager(QObject):
    """
    Manages a global hotkey listener using pynput. It parses a hotkey
    combination from the application's config and can be reconfigured on the fly.
    """

    hotkey_triggered = Signal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._target_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        self._current_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        self._listener: keyboard.Listener | None = None
        self._listener_thread: Thread | None = None

    @staticmethod
    def _parse_hotkey_string(hotkey_str: str) -> set[keyboard.Key | keyboard.KeyCode]:
        """
        Parses a user-friendly hotkey string (e.g., "ctrl+shift+f7") into a
        set of pynput key objects. Returns an empty set if parsing fails.
        """

        target_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        log.info(f"Attempting to parse global hotkey: '{hotkey_str}'")

        if not hotkey_str:
            log.error("Hotkey string is empty. Hotkey will be disabled.")
            return set()

        key_parts = [part.strip().lower() for part in hotkey_str.split("+")]
        for part in key_parts:
            try:
                # First, try to match special keys from the enum (e.g., 'f7', 'ctrl_l', 'shift')
                key = keyboard.Key[part]
            except KeyError:
                # If that fails, assume it's a normal character (e.g., 'a', '7')
                if len(part) == 1:
                    key = keyboard.KeyCode.from_char(part)
                else:
                    log.error(
                        f"Invalid key name '{part}' in hotkey. Please use names like 'f7', 'ctrl', 'shift', 'alt', or single characters. Hotkey will be disabled."
                    )
                    return set()
            target_keys.add(key)

        if not target_keys:
            log.warning("No valid keys found after parsing. Hotkey will be disabled.")
        else:
            log.info(f"Successfully parsed hotkey. Target keys: {target_keys}")

        return target_keys

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode):
        """Callback for when pynput detects a key press."""

        self._current_keys.add(key)
        if self._current_keys == self._target_keys:
            log.info("Global hotkey combination pressed!")
            self.hotkey_triggered.emit()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode):
        """Callback for when pynput detects a key release."""

        self._current_keys.discard(key)

    def start_listener(self):
        """
        Starts the keyboard listener in a separate thread. This should only be
        called once at application startup.
        """

        self._target_keys = self._parse_hotkey_string(self._config.ui.hotkey)
        if not self._target_keys:
            log.warning("Cannot start listener: hotkey is invalid.")
            return

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)  # pyright: ignore[reportArgumentType]
        self._listener_thread = Thread(target=self._listener.run, name="hotkey-listener", daemon=True)
        self._listener_thread.start()
        log.info("Global hotkey listener started.")

    def stop_listener(self):
        """Stops the keyboard listener thread."""

        if self._listener:
            self._listener.stop()
            log.info("Global hotkey listener stopped.")

    def on_config_changed(self, new_config: AppConfig):
        """
        Hot-reloads the hotkey by stopping the old listener and starting a new one.
        """

        log.info("Configuration changed. Re-initializing hotkey listener.")
        self.stop_listener()

        # Update internal config and restart with the new hotkey
        self._config = new_config
        self.start_listener()
