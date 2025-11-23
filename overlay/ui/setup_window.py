from typing import final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QFrame,
    QSpacerItem,
    QSizePolicy,
)


@final
class SetupWindow(QDialog):
    """
    A dialog that prompts the user for their Spotify Client ID.
    Inherits styling from the global qt_material theme.
    """

    client_id_saved = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spoverlay - Setup")
        self.setFixedSize(500, 320)
        self.setWindowFlags(Qt.WindowType.Dialog)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("Welcome to Spoverlay")
        title.setStyleSheet("font-weight: bold; font-size: 16pt;")

        subtitle = QLabel("Before we start let's make sure you have your Client ID set up.")
        subtitle.setStyleSheet("font-size: 11pt;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        instructions = QLabel(
            """
            Spoverlay needs your personal <b>Spotify Client ID</b> to work.
            <br><br>
            Please follow the <i>'Create Spotify App'</i> guide in the <a href='https://github.com/edryal/spoverlay#4-create-spotify-app'>README</a> to generate one.
            """
        )
        instructions.setOpenExternalLinks(True)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-size: 10pt;")
        main_layout.addWidget(instructions)

        input_layout = QVBoxLayout()
        input_layout.setSpacing(4)

        lbl_input = QLabel("Enter Client ID:")
        lbl_input.setStyleSheet("font-weight: bold;")

        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("e.g., 34a9b8d7...")

        self.error_label = QLabel("Invalid Client ID (must be 32 characters)")
        self.error_label.setStyleSheet("color: #ff5555; font-size: 9pt;")
        self.error_label.hide()

        input_layout.addWidget(lbl_input)
        input_layout.addWidget(self.client_id_input)
        input_layout.addWidget(self.error_label)
        main_layout.addLayout(input_layout)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        button_layout = QHBoxLayout()

        self.quit_button = QPushButton("Quit")
        self.quit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        _ = self.quit_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Save && Connect")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.setDefault(True)
        _ = self.save_button.clicked.connect(self._on_save)

        button_layout.addWidget(self.quit_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

        _ = self.client_id_input.textChanged.connect(lambda: self.error_label.hide())

    def _on_save(self):
        client_id = self.client_id_input.text().strip()

        """
        Client IDs are 32 characters long so we'll check for that.
        In case the ID was not fully copied. Classic user error.
        """
        if len(client_id) != 32:
            self.client_id_input.setFocus()
            self.error_label.show()
            return

        self.client_id_saved.emit(client_id)
        self.accept()
