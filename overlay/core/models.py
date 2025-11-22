from dataclasses import dataclass

@dataclass
class SpotifyConfig:
    client_id: str
    redirect_uri: str

@dataclass
class UIConfig:
    position: str  # top-left, top-right, bottom-left, bottom-right
    margin: int
    click_through: bool
    art_size: int
    hotkey: str

@dataclass
class AppConfig:
    spotify: SpotifyConfig
    ui: UIConfig
    poll_interval_ms: int
    app_directory: str
    data_directory: str
    config_path: str

@dataclass(frozen=True)
class NowPlaying:
    title: str
    artist: str
    album: str
    album_art_url: str | None
    is_playing: bool
    progress_ms: int
    duration_ms: int
