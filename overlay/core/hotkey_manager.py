# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportUnknownParameterType=false

import os
import logging
from threading import Thread
from typing import final

from pynput import keyboard

from PySide6.QtCore import QObject, Signal

"""
Manages a global hotkey listener that works cross-platform.
The hotkey is configured via the OVERLAY_HOTKEY environment variable.
"""


@final
class GlobalHotkeyManager(QObject):
    hotkey_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = logging.getLogger("overlay.core.hotkey")

        # State for tracking pressed keys
        self._target_keys = set()
        self._current_keys = set()

        self._listener_thread = None
        self._listener = None

        self._parse_hotkey_from_env()

    def _parse_hotkey_from_env(self):
        """
        Parses the OVERLAY_HOTKEY environment variable and populates the target_keys set.
        Defaults to "F7"
        """

        hotkey_str = os.environ.get("OVERLAY_HOTKEY", "f7").lower()
        self.log.info(f"Attempting to use global hotkey combination: {hotkey_str}")

        key_parts = hotkey_str.split("+")
        for part in key_parts:
            try:
                key = keyboard.Key[part]
            except KeyError:
                if len(part) == 1:
                    key = keyboard.KeyCode.from_char(part)
                else:
                    self.log.error(f"Invalid key name '{part}' in hotkey string.")
                    self._target_keys.clear()
                    return
            self._target_keys.add(key)

        if not self._target_keys:
            self.log.error("Hotkey could not be parsed. No listener will be started.")
        else:
            self.log.info(f"Successfully parsed hotkey. Target keys: {self._target_keys}")

    def _on_press(self, key):
        # Callback for when a key is pressed.
        self._current_keys.add(key)
        if self._current_keys == self._target_keys:
            self.log.info("Global hotkey combination pressed!")
            self.hotkey_triggered.emit()

    def _on_release(self, key):
        # Callback for when a key is released.
        try:
            self._current_keys.remove(key)
        except KeyError:
            pass

    def start_listener(self):
        # Starts the keyboard listener in a separate thread.
        if not self._target_keys:
            self.log.error("Cannot start listener: hotkey is not valid.")
            return

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)

        self._listener_thread = Thread(target=self._listener.run, daemon=True)
        self._listener_thread.start()
        self.log.info("Global hotkey listener started.")

    def stop_listener(self):
        # Stops the keyboard listener.
        if self._listener:
            self._listener.stop()
        self.log.info("Global hotkey listener stopped.")
