from dataclasses import dataclass


@dataclass(frozen=True)
class NowPlaying:
    title: str
    artist: str
    album: str
    album_art_url: str | None
    is_playing: bool
    progress_ms: int
    duration_ms: int
