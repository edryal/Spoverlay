import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


def _user_data_dir(app_name: str) -> str:
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return os.path.join(base, app_name)
    else:
        base = os.environ.get("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        return os.path.join(base, app_name)


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


@dataclass
class AppConfig:
    spotify: SpotifyConfig
    ui: UIConfig
    poll_interval_ms: int
    app_directory: str
    data_directory: str

"""
Loads all the environment variables
required for the overlay to run properly
"""

def load_config() -> AppConfig:
    # Mostly for the .env file from this project's directory
    # But I guess it's only useful while developing
    _ = load_dotenv()

    # Spotify credentials that need to be created
    # in the spotify developer dashboard
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    if not client_id:
        raise RuntimeError("Missing SPOTIFY_CLIENT_ID environment variable")

    if not redirect_uri:
        raise RuntimeError("Missing SPOTIFY_REDIRECT_URI environment variable")

    # UI settings
    # These are some pretty sane defaults
    position = os.environ.get("OVERLAY_POSITION", "top-right").strip().lower()
    margin = int(os.environ.get("OVERLAY_MARGIN", "24"))
    click_through = os.environ.get("OVERLAY_CLICK_THROUGH", "1") not in ("0", "false", "no")
    art_size = int(os.environ.get("OVERLAY_ART_SIZE", "64"))

    # Interval between "updates" basically. Affects the responsiveness
    # of the overlay when the music is paused or unpaused.
    # Defaults to 1000ms
    poll_interval_ms = int(os.environ.get("POLL_INTERVAL_MS", "1000"))

    # Current app directory so that assets/tray-icon can be found
    app_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Location where the cached token will be stored
    data_directory = _user_data_dir("Spoverlay")

    return AppConfig(
        spotify=SpotifyConfig(client_id=client_id, redirect_uri=redirect_uri),
        ui=UIConfig(position=position, margin=margin, click_through=click_through, art_size=art_size),
        poll_interval_ms=poll_interval_ms,
        app_directory=app_directory,
        data_directory=data_directory,
    )
