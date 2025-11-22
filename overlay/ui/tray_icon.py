# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAny=false, reportPossiblyUnboundVariable=false, reportUnannotatedClassAttribute=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false

import logging

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from overlay.core.models import AppConfig
from overlay.core.spotify_client import SpotifyClient
from overlay.ui.configure_window import ConfigureWindow
from overlay.ui.overlay_window import OverlayWindow


ACTION_TOGGLE_VISIBILITY = "Show Overlay"
ACTION_CONFIGURE = "Configure"
ACTION_RELOGIN = "Clear Cache && Relogin"
ACTION_QUIT = "Quit"

log = logging.getLogger(__name__)


class TrayIcon(QSystemTrayIcon):
    """
    Manages the application's system tray icon, its context menu, and all
    user interactions originating from the tray, such as toggling visibility,
    re-authenticating, and accessing the configuration window.
    """

    def __init__(self, app_name: str, icon_path: str, window: OverlayWindow, spotify_client: SpotifyClient, config: AppConfig):
        app_instance = QApplication.instance()
        super().__init__(app_instance)

        self._window = window
        self._spotify_client = spotify_client

        self.setIcon(QIcon(icon_path))
        self.setToolTip(app_name)

        self._user_wants_visible = window.isVisible()
        self._window.user_visibility_state = self._user_wants_visible

        self.configure_window = ConfigureWindow(config)
        self._toggle_action = QAction(ACTION_TOGGLE_VISIBILITY, self)
        self.setContextMenu(self._build_menu())

        _ = self.activated.connect(self._on_activated)
        self.show()
        log.info("System tray icon initialized.")

    def _build_menu(self) -> QMenu:
        """Creates and returns the context menu for the tray icon."""

        menu = QMenu()

        self._toggle_action.setCheckable(True)
        self._toggle_action.setChecked(self._user_wants_visible)
        _ = self._toggle_action.triggered.connect(self._on_toggle_visibility_from_menu)
        menu.addAction(self._toggle_action)

        configure_action = QAction(ACTION_CONFIGURE, self)
        _ = configure_action.triggered.connect(self._show_configure_window)
        menu.addAction(configure_action)

        _ = menu.addSeparator()

        relogin_action = QAction(ACTION_RELOGIN, self)
        _ = relogin_action.triggered.connect(self._on_relogin)
        menu.addAction(relogin_action)

        _ = menu.addSeparator()

        quit_action = QAction(ACTION_QUIT, self)
        _ = quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        return menu

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handles left-click activation on the tray icon."""

        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        """Toggles the desired visibility state of the overlay."""

        new_state = not self._user_wants_visible
        self._set_visibility_and_update_ui(new_state)

    def _set_visibility_and_update_ui(self, new_state: bool):
        """
        Updates the internal state, the menu checkbox, and the window itself.
        """

        self._user_wants_visible = new_state
        self._window.user_visibility_state = self._user_wants_visible

        if self._toggle_action:
            self._toggle_action.setChecked(new_state)

        if new_state:
            self._window.set_now_playing(self._window.get_last_now_playing())
        else:
            self._window.hide()

    def _on_toggle_visibility_from_menu(self, checked: bool):
        """Handler for when the user clicks the 'Show Overlay' checkbox."""

        self._set_visibility_and_update_ui(checked)

    def _on_relogin(self):
        """
        Handles the relogin action, preserving the user's visibility preference.
        """

        log.info("User requested to clear cache and relogin.")

        was_visible_before_relogin = self._user_wants_visible
        if was_visible_before_relogin:
            self._set_visibility_and_update_ui(False)

        self._spotify_client.relogin()

        self._user_wants_visible = was_visible_before_relogin
        self._window.user_visibility_state = was_visible_before_relogin
        self._toggle_action.setChecked(was_visible_before_relogin)

    def _show_configure_window(self):
        """Shows the configuration window, ensuring it is raised to the front."""

        log.info("Opening configuration window.")
        self.configure_window.show()
        self.configure_window.raise_()
        self.configure_window.activateWindow()
