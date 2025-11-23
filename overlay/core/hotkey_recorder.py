# pyright: reportUnknownMemberType = false, reportUnknownArgumentType = false

from typing import override

from PySide6.QtGui import QKeyEvent, Qt
from PySide6.QtWidgets import QLineEdit


class HotkeyRecorder(QLineEdit):
    """
    A custom QLineEdit that captures key combinations instead of text input.
    It formats the keys into a string compatible with pynput (e.g., 'ctrl+shift+f7').
    """

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Click to record...")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setStyleSheet(
            """
            QLineEdit {
                selection-background-color: transparent; 
            }
            QLineEdit:focus {
                border: 1px solid #3584e4;
                background-color: #2d2d2d;
            }
        """
        )

    @override
    def keyPressEvent(self, event: QKeyEvent):  # pyright: ignore[reportIncompatibleMethodOverride]
        key = event.key()
        modifiers = event.modifiers()

        # Clearing
        if key == Qt.Key.Key_Backspace or key == Qt.Key.Key_Delete:
            self.setText("")
            return

        # Cancellation (Esc) - lose focus without changing
        if key == Qt.Key.Key_Escape:
            self.clearFocus()
            return

        # Filter out standalone modifier presses, like just pressing Ctrl
        # We wait for a non-modifier key to complete the sequence.
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        parts = []

        # Order: Ctrl -> Shift -> Alt -> Meta -> Key
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("CTRL")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("SHIFT")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("ALT")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("WIN")

        # Map the primary key to a string
        key_text = self._map_qt_key_to_string(key)
        if not key_text:
            return

        parts.append(key_text)

        final_hotkey = "+".join(parts)
        self.setText(final_hotkey)
        self.clearFocus()

    def _map_qt_key_to_string(self, qt_key: int) -> str | None:
        """Maps Qt key codes to pynput-compatible string representations."""

        # Function Keys
        # F1 = 100, F5 = 104, let's assume wa want qt_key = F5
        # 104 - 100 = 4, but we want F5 to show, so we do +1
        if Qt.Key.Key_F1 <= qt_key <= Qt.Key.Key_F12:
            return f"F{qt_key - Qt.Key.Key_F1 + 1}"

        # Alphanumeric (A-Z, 0-9)
        if Qt.Key.Key_A <= qt_key <= Qt.Key.Key_Z:
            return chr(qt_key).upper()

        if Qt.Key.Key_0 <= qt_key <= Qt.Key.Key_9:
            return chr(qt_key)

        # Common Special Keys
        mapping = {
            Qt.Key.Key_Space: "SPACE",
            Qt.Key.Key_Tab: "TAB",
            Qt.Key.Key_Return: "ENTER",
            Qt.Key.Key_Enter: "ENTER",
            Qt.Key.Key_Insert: "INSERT",
            Qt.Key.Key_Home: "HOME",
            Qt.Key.Key_End: "END",
            Qt.Key.Key_PageUp: "PAGE_UP",
            Qt.Key.Key_PageDown: "PAGE_DOWN",
            Qt.Key.Key_Minus: "-",
            Qt.Key.Key_Equal: "=",
            Qt.Key.Key_BracketLeft: "[",
            Qt.Key.Key_BracketRight: "]",
            Qt.Key.Key_Backslash: "\\",
            Qt.Key.Key_Semicolon: ";",
            Qt.Key.Key_Apostrophe: "'",
            Qt.Key.Key_Comma: ",",
            Qt.Key.Key_Period: ".",
            Qt.Key.Key_Slash: "/",
            Qt.Key.Key_QuoteLeft: "`",
        }

        return mapping.get(qt_key, None)  # pyright: ignore[reportCallIssue, reportUnknownVariableType, reportArgumentType]
