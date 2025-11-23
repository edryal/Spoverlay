# pyright: reportAny=false, reportUnknownMemberType=false

import logging
import os
import sys

import toml

from overlay.core.models import AppConfig, SpotifyConfig, UIConfig


APP_NAME = "Spoverlay"
CONFIG_FILE_NAME = "config.toml"
DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8080/callback"
DEFAULT_SPOTIFY_POLL_INTERVAL = 1000
DEFAULT_HOTKEY = "F7"

log = logging.getLogger(__name__)


def user_data_dir() -> str:
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
    return os.path.join(base, APP_NAME)


def get_default_config() -> AppConfig:
    app_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_directory = user_data_dir()

    return AppConfig(
        client=SpotifyConfig(
            client_id="",
            redirect_uri=DEFAULT_SPOTIFY_REDIRECT_URI,
            poll_interval_ms=DEFAULT_SPOTIFY_POLL_INTERVAL,
        ),
        ui=UIConfig(position="top-right", margin=24, click_through=True, art_size=64, hotkey=DEFAULT_HOTKEY),
        app_directory=app_directory,
        data_directory=data_directory,
        config_path=os.path.join(data_directory, CONFIG_FILE_NAME),
    )


def save_config(config: AppConfig):
    config_to_save = {
        "client": {
            "client_id": config.client.client_id,
            "redirect_uri": config.client.redirect_uri,
            "poll_interval_ms": config.client.poll_interval_ms,
        },
        "ui": {
            "position": config.ui.position,
            "margin": config.ui.margin,
            "click_through": config.ui.click_through,
            "art_size": config.ui.art_size,
            "hotkey": config.ui.hotkey,
        },
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

    """
    Load from the file, but don't crash, just use default values.
    This allows the user to access the configuration window, where
    he can attempt again to change the settings.
    """
    try:
        with open(config.config_path, "r") as f:
            user_config = toml.load(f)
    except toml.TomlDecodeError as e:
        log.warning(f"Failed to decode config file, using defaults. Error: {e}")
        return config

    ui_section = user_config.get("ui", {})
    if isinstance(ui_section, dict):
        try:
            config.ui.position = str(ui_section.get("position", config.ui.position))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.margin = int(ui_section.get("margin", config.ui.margin))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.art_size = int(ui_section.get("art_size", config.ui.art_size))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.click_through = bool(ui_section.get("click_through", config.ui.click_through))  # pyright: ignore[reportUnknownArgumentType]
            config.ui.hotkey = str(ui_section.get("hotkey", config.ui.hotkey))  # pyright: ignore[reportUnknownArgumentType]
        except (ValueError, TypeError):
            log.warning("Invalid value in 'ui' section of config, using defaults for affected keys.")

    client_section = user_config.get("client", {})
    if isinstance(client_section, dict):
        try:
            config.client.client_id = str(client_section.get("client_id", config.client.client_id))  # pyright: ignore[reportUnknownArgumentType]
            config.client.redirect_uri = str(client_section.get("redirect_uri", config.client.redirect_uri))  # pyright: ignore[reportUnknownArgumentType]
            config.client.poll_interval_ms = int(user_config.get("poll_interval_ms", config.client.poll_interval_ms))
        except (ValueError, TypeError):
            log.warning("Invalid value in 'client' section of config, using defaults for affected keys.")

    return config
