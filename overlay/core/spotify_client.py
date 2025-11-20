# pyright: reportAny=false, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

import os
import threading
import time
from typing import final

import spotipy
from spotipy.oauth2 import SpotifyPKCE
from PySide6.QtCore import QObject, Signal

from overlay.core.config import AppConfig
from overlay.core.state import NowPlaying


@final
class SpotifyClient(QObject):
    now_playing_updated = Signal(object)

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config

        # Limit the scope of the client
        # So that we don't fuck up anything
        scope = "user-read-playback-state user-read-currently-playing"

        cache_path = os.path.join(config.data_directory, "spotify_token_cache")
        os.makedirs(config.data_directory, exist_ok=True)

        # SpotifyPKCE is used since it doesn't require a secret
        # Also for some reason the auth link that is generated
        # when you start the app for the first time works more consistently
        auth = SpotifyPKCE(
            client_id=config.spotify.client_id,
            redirect_uri=config.spotify.redirect_uri,
            scope=scope,
            cache_path=cache_path,
            open_browser=True,
        )
        self._sp = spotipy.Spotify(auth_manager=auth)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last: NowPlaying | None = None
        self._interval = max(0.25, config.poll_interval_ms / 1000.0)

    """
    Get all the data from the currently playing track.
    Two attepts to fetch before it gives up.

    This function most probably needs a refactor.
    """
    def get_current(self) -> NowPlaying | None:
        data = None
        try:
            data = self._sp.current_user_playing_track()
        except Exception:
            try:
                data = self._sp.current_user_playing_track()
            except Exception:
                return None

        if not data or not data.get("item"):
            return None

        item = data["item"]
        is_playing = bool(data.get("is_playing", False))
        progress_ms = int(data.get("progress_ms") or 0)
        duration_ms = int(item.get("duration_ms") or 0)
        title = item.get("name") or ""
        artists = ", ".join(a.get("name") for a in item.get("artists", []) if a and a.get("name"))
        album = (item.get("album") or {}).get("name") or ""
        images = (item.get("album") or {}).get("images") or []
        album_art_url = images[0]["url"] if images else None

        return NowPlaying(
            title=title,
            artist=artists,
            album=album,
            album_art_url=album_art_url,
            is_playing=is_playing,
            progress_ms=progress_ms,
            duration_ms=duration_ms,
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
