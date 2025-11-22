# pyright: reportAny=false, reportUnknownMemberType=false
import os
import sys
import logging

import toml

from overlay.core.models import AppConfig, SpotifyConfig, UIConfig


APP_NAME = "Spoverlay"
CONFIG_FILE_NAME = "config.toml"
SPOTIFY_CLIENT_ID = "1a8fda4857f04abfa5a6f13fd7444af3"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8080/callback"
DEFAULT_HOTKEY = "F7"

log = logging.getLogger(__name__)


def _user_data_dir() -> str:
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
    return os.path.join(base, APP_NAME)


def get_default_config() -> AppConfig:
    app_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_directory = _user_data_dir()

    return AppConfig(
        spotify=SpotifyConfig(
            client_id=SPOTIFY_CLIENT_ID,
            redirect_uri=SPOTIFY_REDIRECT_URI,
        ),
        ui=UIConfig(position="top-right", margin=24, click_through=True, art_size=64, hotkey=DEFAULT_HOTKEY),
        poll_interval_ms=1000,
        app_directory=app_directory,
        data_directory=data_directory,
        config_path=os.path.join(data_directory, CONFIG_FILE_NAME),
    )


def save_config(config: AppConfig):
    config_to_save = {
        "ui": {
            "position": config.ui.position,
            "margin": config.ui.margin,
            "click_through": config.ui.click_through,
            "art_size": config.ui.art_size,
            "hotkey": config.ui.hotkey,
        },
        "poll_interval_ms": config.poll_interval_ms,
    }
    try:
        os.makedirs(os.path.dirname(config.config_path), exist_ok=True)
        with open(config.config_path, "w") as f:
            _ = toml.dump(config_to_save, f)
    except (IOError, OSError) as e:
        log.error(f"Failed to save configuration to {config.config_path}: {e}")


def load_config() -> AppConfig:
    """
    Loads configuration from the user's file, safely falling back to defaults
    for any missing or invalid values. Creates the file if it doesn't exist.
    """
    # Start with a fresh copy of the defaults.
    config = get_default_config()

    # Create the config file from defaults if it's missing.
    if not os.path.exists(config.config_path):
        save_config(config)
        return config

    # Load from the file, but don't crash on corruption.
    try:
        with open(config.config_path, "r") as f:
            user_config = toml.load(f)
    except toml.TomlDecodeError as e:
        log.warning(f"Failed to decode config file, using defaults. Error: {e}")
        return config

    try:
        config.poll_interval_ms = int(user_config.get("poll_interval_ms", config.poll_interval_ms))
    except (ValueError, TypeError):
        log.warning("Invalid 'poll_interval_ms' in config, using default.")

    user_ui_section = user_config.get("ui", {})
    if isinstance(user_ui_section, dict):
        try:
            config.ui.position = str(user_ui_section.get("position", config.ui.position))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.margin = int(user_ui_section.get("margin", config.ui.margin))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.art_size = int(user_ui_section.get("art_size", config.ui.art_size))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.click_through = bool(user_ui_section.get("click_through", config.ui.click_through))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.hotkey = str(user_ui_section.get("hotkey", config.ui.hotkey))  # pyright: ignore[reportUnknownArgumentType]
        except (ValueError, TypeError):
            log.warning("Invalid value in 'ui' section of config, using defaults for affected keys.")

    return config
