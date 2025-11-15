# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAny=false, reportPossiblyUnboundVariable=false, reportUnannotatedClassAttribute=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false

import logging
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from overlay.ui.overlay_window import OverlayWindow


class TrayIcon(QSystemTrayIcon):
    def __init__(self, app_name: str, app_icon_path: str, window: OverlayWindow, parent=None):  # pyright: ignore[reportMissingParameterType]
        app_instance = QApplication.instance()
        super().__init__(app_instance)
        self._log = logging.getLogger("overlay.ui.tray")
        self._window = window

        self.setIcon(QIcon(app_icon_path))
        self.setToolTip(app_name)
        self._user_wants_visible = window.isVisible()

        self._toggle_action = QAction("Show Overlay", self)
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
        _ = menu.addSeparator()
        quit_action = QAction("Quit", self)
        _= quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        return menu

    def _on_activated(self, reason):  # pyright: ignore[reportMissingParameterType]
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
