# pyright: reportAny=false, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

import logging
import os
import threading
import time
from typing import final

from PySide6.QtCore import QObject, Signal
import spotipy
from spotipy.oauth2 import SpotifyPKCE

from overlay.core.models import AppConfig, NowPlaying


SPOTIFY_SCOPE = "user-read-playback-state user-read-currently-playing"
SPOTIFY_CACHE_FILENAME = "spotify_token_cache"

log = logging.getLogger(__name__)


@final
class SpotifyClient(QObject):
    """
    Manages all communication with the Spotify Web API.
    Handles lazy initialization if configuration is missing.
    """

    now_playing_updated = Signal(object)
    clear_ui_requested = Signal()
    setup_required = Signal() 

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._sp: spotipy.Spotify | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_state: NowPlaying | None = None
        self._poll_interval = max(0.25, config.client.poll_interval_ms / 1000.0)

        self.cache_path = os.path.join(config.data_directory, SPOTIFY_CACHE_FILENAME)
        os.makedirs(config.data_directory, exist_ok=True)

        if not self._config.client.client_id:
            log.info("No Client ID found in config. Waiting for setup...")
        else:
            self._initialize_client()

    def is_configured(self) -> bool:
        """Returns True if the client has a Client ID and is ready to initialize."""

        return bool(self._config.client.client_id)

    def update_credentials(self, new_client_id: str):
        """Called when the user provides credentials via the setup window."""

        log.info("Received new credentials. initializing client...")
        self._config.client.client_id = new_client_id
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the Spotipy client with the current config."""

        try:
            auth_manager = SpotifyPKCE(
                client_id=self._config.client.client_id,
                redirect_uri=self._config.client.redirect_uri,
                scope=SPOTIFY_SCOPE,
                cache_path=self.cache_path,
                open_browser=True,
            )
            self._sp = spotipy.Spotify(auth_manager=auth_manager)
            log.info("Spotify client initialized successfully.")
        except Exception as e:
            log.error(f"Failed to initialize Spotify client: {e}")

    def get_current(self) -> NowPlaying | None:
        """
        Fetches the currently playing track from Spotify, with one retry on failure.
        Returns a NowPlaying object or None if no track is playing.
        """

        if not self._sp:
            return None

        for attempt in range(2):
            try:
                data = self._sp.current_user_playing_track()
                if data and data.get("item"):
                    item = data["item"]
                    album = item.get("album", {})
                    images = album.get("images", [])

                    return NowPlaying(
                        title=item.get("name", ""),
                        artist=", ".join(a["name"] for a in item.get("artists", []) if a and a.get("name")),
                        album=album.get("name", ""),
                        album_art_url=images[0]["url"] if images else None,
                        is_playing=data.get("is_playing", False),
                        progress_ms=data.get("progress_ms", 0),
                        duration_ms=item.get("duration_ms", 0),
                    )
                return None
            except spotipy.SpotifyException as e:
                log.warning(f"Spotify API error on attempt {attempt + 1}: {e}")
                time.sleep(1)
            except Exception as e:
                log.error(f"Unexpected error fetching track on attempt {attempt + 1}: {e}")

        return None

    def start_polling(self) -> None:
        if not self._sp:
            log.warning("Cannot start polling: Spotify client not initialized.")
            return

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_polling_loop, name="spotify-poller", daemon=True)
        self._thread.start()

    def _run_polling_loop(self):
        idle_backoff_seconds = 2.0
        while not self._stop_event.is_set():
            # Double check if the client has been initialized. Just to be sure
            if not self._sp: 
                break

            current_state = self.get_current()
            if current_state != self._last_state:
                self.now_playing_updated.emit(current_state)
                self._last_state = current_state

            sleep_duration = idle_backoff_seconds if (current_state is None or not current_state.is_playing) else self._poll_interval
            time.sleep(sleep_duration)

    def stop(self) -> None:
        """Stops the background polling thread."""

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def relogin(self) -> None:
        """
        Stops polling, clears the UI and token cache, and restarts polling to
        trigger a new authentication flow.
        """

        if not self._sp: return
        
        log.info("Relogin requested. Clearing authentication state...")
        self.stop()

        self.clear_ui_requested.emit()
        self._last_state = None

        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
            except OSError:
                pass

        log.info("Restarting polling to trigger re-authentication.")
        self.start_polling()

    def initial_fetch_and_emit(self) -> None:
        """
        Performs a single, blocking fetch for the current track and emits it.
        This is intended for setting the initial state at application startup.
        """

        if not self._sp: return

        log.info("Performing initial fetch...")
        initial_state = self.get_current()
        self.now_playing_updated.emit(initial_state)
        self._last_state = initial_state

    def on_config_changed(self, new_config: AppConfig):
        """Updates the client's settings when the application config changes."""

        log.info(f"Configuration changed. Updating poll interval to {new_config.client.poll_interval_ms}ms.")
        self._config = new_config
        self._poll_interval = max(0.25, new_config.client.poll_interval_ms / 1000.0)
