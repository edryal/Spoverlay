import logging
from typing import final, override

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from overlay.core.config import get_default_config
from overlay.core.hotkey_recorder import HotkeyRecorder
from overlay.core.models import AppConfig


WINDOW_TITLE = "Configure Spoverlay"
WINDOW_WIDTH, WINDOW_HEIGHT = 400, 420

LABEL_CLIENT_ID = "Client ID:"
LABEL_REDIRECT_URI = "Redirect URI:"
LABEL_POSITION = "Overlay Position:"
LABEL_MARGIN = "Screen Margin (px):"
LABEL_ART_SIZE = "Album Art Size (px):"
LABEL_POLL_INTERVAL = "Update Interval (ms):"
LABEL_HOTKEY = "Global Hotkey:"
CHECKBOX_CLICK_THROUGH = "Overlay Click-Through"

BUTTON_RESET = "Reset to Default"
BUTTON_SAVE = "Save && Apply"
BUTTON_CANCEL = "Cancel"

SPINBOX_MARGIN_RANGE = (0, 500)
SPINBOX_ART_SIZE_RANGE = (32, 256)
SPINBOX_POLL_INTERVAL_RANGE = (100, 5000)

log = logging.getLogger(__name__)


@final
class ConfigureWindow(QWidget):
    """
    A dialog window that allows the user to view and modify the application's
    configuration. It emits a `config_saved` signal with the updated config
    object when the user saves their changes.
    """

    config_saved = Signal(AppConfig)

    def __init__(self, config: AppConfig):
        super().__init__()

        # This holds a reference to the application's single, shared config object.
        self._shared_config = config
        self._defaults = get_default_config()

        self.client_id_input: QLineEdit
        self.redirect_uri_input: QLineEdit
        self.position_choice: QComboBox
        self.margin_spinbox: QSpinBox
        self.art_size_spinbox: QSpinBox
        self.poll_interval_spinbox: QSpinBox
        self.hotkey_input: HotkeyRecorder
        self.click_through_checkbox: QCheckBox

        self._create_widgets()
        self._layout_widgets()
        self._connect_signals()
        self._setup_window_flags()

    def _create_widgets(self):
        """Initializes all the child widgets for the configuration window."""

        self.client_id_input = QLineEdit()
        self.client_id_input.setReadOnly(True)
        self.client_id_input.setPlaceholderText("Not configured")
        self.client_id_input.setStyleSheet("color: #888;")

        self.redirect_uri_input = QLineEdit()
        self.redirect_uri_input.setReadOnly(True)
        self.redirect_uri_input.setStyleSheet("color: #888;")

        self.position_choice = QComboBox()
        self.position_choice.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])

        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(*SPINBOX_MARGIN_RANGE)

        self.art_size_spinbox = QSpinBox()
        self.art_size_spinbox.setRange(*SPINBOX_ART_SIZE_RANGE)
        self.art_size_spinbox.setSingleStep(8)

        self.poll_interval_spinbox = QSpinBox()
        self.poll_interval_spinbox.setRange(*SPINBOX_POLL_INTERVAL_RANGE)
        self.poll_interval_spinbox.setSingleStep(100)

        self.hotkey_input = HotkeyRecorder()
        self.click_through_checkbox = QCheckBox(CHECKBOX_CLICK_THROUGH)

    def _layout_widgets(self):
        """Arranges the created widgets using layouts."""

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setSpacing(10)

        # Auth (Read Only)
        header_auth = QLabel("<b>Spotify Settings</b>")
        header_auth.setStyleSheet("margin-bottom: 5px;")
        form_layout.addRow(header_auth)
        form_layout.addRow(LABEL_CLIENT_ID, self.client_id_input)
        form_layout.addRow(LABEL_REDIRECT_URI, self.redirect_uri_input)
        
        form_layout.addRow(QLabel("")) 

        # Preferences
        header_pref = QLabel("<b>Appearance & Behavior</b>")
        header_pref.setStyleSheet("margin-bottom: 5px;")
        form_layout.addRow(header_pref)
        form_layout.addRow(LABEL_POSITION, self.position_choice)
        form_layout.addRow(LABEL_MARGIN, self.margin_spinbox)
        form_layout.addRow(LABEL_ART_SIZE, self.art_size_spinbox)
        form_layout.addRow(LABEL_POLL_INTERVAL, self.poll_interval_spinbox)
        form_layout.addRow(LABEL_HOTKEY, self.hotkey_input)
        
        main_layout.addLayout(form_layout)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.click_through_checkbox)
        checkbox_layout.addStretch()
        main_layout.addLayout(checkbox_layout)

        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton(BUTTON_RESET)
        self.save_button = QPushButton(BUTTON_SAVE)
        self.save_button.setDefault(True)
        self.close_button = QPushButton(BUTTON_CANCEL)

        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connects the button click signals to their respective handlers."""

        _ = self.reset_button.clicked.connect(self._on_reset)
        _ = self.save_button.clicked.connect(self._on_save)
        _ = self.close_button.clicked.connect(self.close)

    def _load_config_into_ui(self, source: AppConfig):
        """Populates the UI fields from a given config object."""

        self.client_id_input.setText(source.client.client_id)
        self.redirect_uri_input.setText(source.client.redirect_uri)
        self.position_choice.setCurrentText(source.ui.position)
        self.margin_spinbox.setValue(source.ui.margin)
        self.art_size_spinbox.setValue(source.ui.art_size)
        self.click_through_checkbox.setChecked(source.ui.click_through)
        self.poll_interval_spinbox.setValue(source.client.poll_interval_ms)
        self.hotkey_input.setText(source.ui.hotkey)

    def _on_save(self):
        """
        Updates the shared config object with values from the UI, emits a
        signal to notify the rest of the application, and closes the window.
        """

        log.info("Saving new configuration.")

        # Modify the shared config object directly.
        self._shared_config.client.client_id = self.client_id_input.text()
        self._shared_config.client.redirect_uri = self.redirect_uri_input.text()
        self._shared_config.ui.position = self.position_choice.currentText()
        self._shared_config.ui.margin = self.margin_spinbox.value()
        self._shared_config.ui.click_through = self.click_through_checkbox.isChecked()
        self._shared_config.ui.art_size = self.art_size_spinbox.value()
        self._shared_config.client.poll_interval_ms = self.poll_interval_spinbox.value()
        self._shared_config.ui.hotkey = self.hotkey_input.text()

        # Emit the signal containing the reference to the now-modified shared object.
        self.config_saved.emit(self._shared_config)
        _ = self.close()

    def _on_reset(self):
        """Loads the default settings into the UI for preview."""

        log.info("Resetting settings to default values (preserving auth).")
        self._load_config_into_ui(self._defaults)

        self.client_id_input.setText(self._shared_config.client.client_id)
        self.redirect_uri_input.setText(self._shared_config.client.redirect_uri)

    @override
    def showEvent(self, event: QShowEvent):
        """
        Overrides QWidget.showEvent to ensure the UI is populated with the
        latest values from the shared config object every time it is shown.
        """

        self._load_config_into_ui(self._shared_config)
        super().showEvent(event)

    def _setup_window_flags(self):
        """Sets the window title, flags, and size."""

        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
