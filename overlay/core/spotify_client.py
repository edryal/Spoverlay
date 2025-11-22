# pyright: reportAny=false, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

import logging
import os
import threading
import time
from typing import final

import spotipy
from spotipy.oauth2 import SpotifyPKCE
from PySide6.QtCore import QObject, Signal

from overlay.core.models import AppConfig, NowPlaying


@final
class SpotifyClient(QObject):
    now_playing_updated = Signal(object)
    clear_ui_requested = Signal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self.log = logging.getLogger("overlay.core.spotify_client")

        # Limit the scope of the client
        # So that we don't fuck up anything
        scope = "user-read-playback-state user-read-currently-playing"

        self.cache_path = os.path.join(config.data_directory, "spotify_token_cache")
        os.makedirs(config.data_directory, exist_ok=True)

        # SpotifyPKCE is used since it doesn't require a secret
        auth = SpotifyPKCE(
            client_id="1a8fda4857f04abfa5a6f13fd7444af3",
            redirect_uri="http://127.0.0.1:8080/callback",
            scope=scope,
            cache_path=self.cache_path,
            open_browser=True,
        )
        self._sp = spotipy.Spotify(auth_manager=auth)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last: NowPlaying | None = None
        self._interval = max(0.25, config.poll_interval_ms / 1000.0)

    """
    Fetches the data from the currently playing track.
    Two retry attepts before it gives up.

    This function most probably needs a refactor.
    """

    def get_current(self) -> NowPlaying | None:
        # Fetches the currently playing track from Spotify. Retries once on failure.
        data = None
        for attempt in range(2):
            try:
                data = self._sp.current_user_playing_track()
                if data and data.get("item"):
                    break
                # If there's no data or no item, it means nothing is playing.
                # We can return None immediately without retrying.
                return None
            except spotipy.SpotifyException as e:
                self.log.warning(f"Spotify API error on attempt {attempt + 1}: {e}")
                # If it's the last attempt just quit
                if attempt == 1:
                    return None
            except Exception as e:
                # Catch any other unexpected errors
                self.log.error(f"Unexpected error fetching track on attempt {attempt + 1}: {e}")
                if attempt == 1:
                    return None

        # If the loop completed but data is somehow still None (shouldn't happen with the break)
        if not data or not data.get("item"):
            return None

        item = data["item"]
        album = item.get("album", {})
        images = album.get("images", [])
        album_art_url = images[0]["url"] if images else None
        artists = ", ".join(a["name"] for a in item.get("artists", []) if a and a.get("name"))

        return NowPlaying(
            title=item.get("name", ""),
            artist=artists,
            album=album.get("name", ""),
            album_art_url=album_art_url,
            is_playing=data.get("is_playing", False),
            progress_ms=data.get("progress_ms", 0),
            duration_ms=item.get("duration_ms", 0),
        )

    def start_polling(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _run():
            idle_backoff = 2.0
            while not self._stop.is_set():
                currently = self.get_current()
                if currently != self._last:
                    self.now_playing_updated.emit(currently)
                    self._last = currently
                time.sleep(idle_backoff if (currently is None or not currently.is_playing) else self._interval)

        self._stop.clear()
        self._thread = threading.Thread(target=_run, name="spotify-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    """
    Stops polling, deletes the token cache, and restarts the polling
    thread to trigger a new authentication attempt.
    """

    def relogin(self) -> None:
        """
        Stops polling, deletes the token cache, and restarts polling to
        trigger a new authentication flow.
        """
        self.log.info("Attempting to relogin...")
        self.stop()

        self.clear_ui_requested.emit()
        self._last = None

        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
                self.log.info(f"Successfully removed token cache at {self.cache_path}")
            except OSError as e:
                self.log.error(f"Failed to remove token cache: {e}")

        if self._last is not None:
            self.now_playing_updated.emit(None)
            self._last = None

        self.log.info("Restarting polling to trigger re-authentication.")
        self.start_polling()

    """
    Performs a single, blocking fetch for the current track and emits it.
    This is intended to be called at application startup to set the initial state.
    """

    def initial_fetch_and_emit(self) -> None:
        self.log.info("Performing initial fetch for currently playing track...")
        initial_state = self.get_current()
        self.now_playing_updated.emit(initial_state)
        self._last = initial_state

    def on_config_changed(self, new_config: AppConfig):
        self._config = new_config
        self._interval = max(0.25, new_config.poll_interval_ms / 1000.0)
