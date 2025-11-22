# pyright: reportGeneralTypeIssues=false, reportUnknownMemberType=false
import logging
import os
import socket
from threading import Thread
from typing import final

from PySide6.QtCore import QObject, Signal


log = logging.getLogger(__name__)


@final
class IpcListener(QObject):
    """
    Listens on a UNIX socket for connections to trigger actions.
    This serves as the "hotkey" mechanism for Linux/Wayland environments
    where global keyboard hooks are unreliable or discouraged.
    """

    toggle_visibility_requested = Signal()

    def __init__(self, socket_path: str):
        super().__init__()
        self.socket_path = socket_path
        self._running = False
        self._thread = Thread(target=self._run, daemon=True)

        # Clean up any stale socket file from a previous crash
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError as e:
                log.error(f"Failed to remove stale IPC socket file: {e}")

    def start(self):
        """Starts the listener thread."""

        if not self._running:
            self._running = True
            self._thread.start()

    def stop(self):
        """Stops the listener thread gracefully."""

        if self._running:
            self._running = False
            # Briefly connect to the socket to unblock the `server.accept()`
            # call, allowing the loop to terminate.
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    s.connect(self.socket_path)
            except (FileNotFoundError, ConnectionRefusedError, socket.timeout):
                # This is expected if the socket is already closing.
                pass
            self._thread.join(timeout=2.0)
            log.info("IPC listener stopped.")

    def _run(self):
        log.info(f"IPC listener starting at {self.socket_path}")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(self.socket_path)
            server.listen(1)
            # Use a timeout to periodically check if the thread should stop
            server.settimeout(1.0)

            while self._running:
                try:
                    connection, _ = server.accept()  # pyright: ignore[reportAny]
                    connection.close()

                    # Check self._running again in case stop() was called during accept()
                    if self._running:
                        log.info("IPC signal received, requesting visibility toggle.")
                        self.toggle_visibility_requested.emit()
                except socket.timeout:
                    # This is normal, just lets us check the while condition
                    continue
                except Exception as e:
                    if self._running:
                        log.error(f"Error in IPC listener: {e}")
        finally:
            server.close()
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
            log.info("IPC listener has shut down.")
