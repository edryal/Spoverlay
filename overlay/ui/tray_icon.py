# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAny=false, reportPossiblyUnboundVariable=false, reportUnannotatedClassAttribute=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false

import logging
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from overlay.core.models import AppConfig
from overlay.core.spotify_client import SpotifyClient
from overlay.ui.configure_window import ConfigureWindow
from overlay.ui.overlay_window import OverlayWindow

"""
Creates the tray icon with toggle functionality
A configuration window and a way to trigger relogin
"""


class TrayIcon(QSystemTrayIcon):
    def __init__(self, app_name: str, app_icon_path: str, window: OverlayWindow, spotify_client: SpotifyClient, config: AppConfig):
        app_instance = QApplication.instance()
        super().__init__(app_instance)

        self._log = logging.getLogger("overlay.ui.tray")
        self._window = window
        self._spotify_client = spotify_client

        self.setIcon(QIcon(app_icon_path))
        self.setToolTip(app_name)
        self._user_wants_visible = window.isVisible()

        self._toggle_action = QAction("Show Overlay", self)
        self.configure_window = ConfigureWindow(config)

        menu = self._build_menu()
        self.setContextMenu(menu)
        _ = self.activated.connect(self._on_activated)

        self._window.user_visibility_state = self._user_wants_visible
        self.show()
        self._log.info("System tray icon initialized.")

    def _build_menu(self) -> QMenu:
        menu = QMenu()

        self._toggle_action.setCheckable(True)
        self._toggle_action.setChecked(self._user_wants_visible)
        _ = self._toggle_action.triggered.connect(self._on_toggle_visibility_from_menu)
        menu.addAction(self._toggle_action)

        configure_action = QAction("Configure", self)
        _ = configure_action.triggered.connect(self._create_configure_menu)
        menu.addAction(configure_action)

        _ = menu.addSeparator()

        relogin_action = QAction("Clear Cache & Relogin", self)
        _ = relogin_action.triggered.connect(self._on_relogin)
        menu.addAction(relogin_action)

        _ = menu.addSeparator()

        quit_action = QAction("Quit", self)
        _ = quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        return menu

    def _on_relogin(self):
        self._log.info("User requested to clear cache and relogin.")

        was_visible = self._user_wants_visible
        if was_visible:
            self._set_visibility_and_update_ui(False)

        self._spotify_client.relogin()

        self._user_wants_visible = was_visible
        self._window.user_visibility_state = was_visible
        self._toggle_action.setChecked(was_visible)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        new_state = not self._user_wants_visible
        self._set_visibility_and_update_ui(new_state)

    def _set_visibility_and_update_ui(self, new_state: bool):
        self._user_wants_visible = new_state
        self._window.user_visibility_state = self._user_wants_visible

        if self._toggle_action:
            self._toggle_action.setChecked(new_state)

        if new_state:
            self._window.set_now_playing(self._window.get_last_now_playing())
        else:
            self._window.hide()

    def _on_toggle_visibility_from_menu(self, checked: bool):
        self._set_visibility_and_update_ui(checked)

    def _create_configure_menu(self):
        self._log.info("Opening configuration window.")
        self.configure_window.show()
        self.configure_window.raise_()
        self.configure_window.activateWindow()
