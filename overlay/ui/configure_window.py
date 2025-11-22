# pyright: reportGeneralTypeIssues=false
import logging
from typing import final, override

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from overlay.core.config import get_default_config
from overlay.core.models import AppConfig


WINDOW_TITLE = "Configure Spoverlay"
WINDOW_WIDTH, WINDOW_HEIGHT = 400, 250

LABEL_POSITION = "Overlay Position:"
LABEL_MARGIN = "Screen Margin (px):"
LABEL_ART_SIZE = "Album Art Size (px):"
LABEL_POLL_INTERVAL = "Update Interval (ms):"
CHECKBOX_CLICK_THROUGH = "Overlay Click-Through"

BUTTON_RESET = "Reset to Default"
BUTTON_SAVE = "Save & Apply"
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

        self.position_choice: QComboBox
        self.margin_spinbox: QSpinBox
        self.art_size_spinbox: QSpinBox
        self.poll_interval_spinbox: QSpinBox
        self.click_through_checkbox: QCheckBox

        self._create_widgets()
        self._layout_widgets()
        self._connect_signals()
        self._setup_window_flags()

    def _create_widgets(self):
        """Initializes all the child widgets for the configuration window."""

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

        self.click_through_checkbox = QCheckBox(CHECKBOX_CLICK_THROUGH)

    def _layout_widgets(self):
        """Arranges the created widgets using layouts."""

        main_layout = QVBoxLayout(self)

        self._add_widget_with_label(main_layout, self.position_choice, LABEL_POSITION)
        self._add_widget_with_label(main_layout, self.margin_spinbox, LABEL_MARGIN)
        self._add_widget_with_label(main_layout, self.art_size_spinbox, LABEL_ART_SIZE)
        self._add_widget_with_label(main_layout, self.poll_interval_spinbox, LABEL_POLL_INTERVAL)
        main_layout.addWidget(self.click_through_checkbox)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

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

    def _add_widget_with_label(self, layout: QVBoxLayout, widget: QWidget, label_text: str):
        """Helper to create a labeled row in the layout."""

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(label_text))
        hbox.addWidget(widget)
        layout.addLayout(hbox)

    def _connect_signals(self):
        """Connects the button click signals to their respective handlers."""

        _ = self.reset_button.clicked.connect(self._on_reset)
        _ = self.save_button.clicked.connect(self._on_save)
        _ = self.close_button.clicked.connect(self.close)

    def _load_config_into_ui(self, source: AppConfig):
        """Populates the UI fields from a given config object."""

        self.position_choice.setCurrentText(source.ui.position)
        self.margin_spinbox.setValue(source.ui.margin)
        self.art_size_spinbox.setValue(source.ui.art_size)
        self.click_through_checkbox.setChecked(source.ui.click_through)
        self.poll_interval_spinbox.setValue(source.poll_interval_ms)

    def _on_save(self):
        """
        Updates the shared config object with values from the UI, emits a
        signal to notify the rest of the application, and closes the window.
        """

        log.info("Saving new configuration.")

        # Modify the shared config object directly.
        self._shared_config.ui.position = self.position_choice.currentText()
        self._shared_config.ui.margin = self.margin_spinbox.value()
        self._shared_config.ui.click_through = self.click_through_checkbox.isChecked()
        self._shared_config.ui.art_size = self.art_size_spinbox.value()
        self._shared_config.poll_interval_ms = self.poll_interval_spinbox.value()

        # Emit the signal containing the reference to the now-modified shared object.
        self.config_saved.emit(self._shared_config)
        _ = self.close()

    def _on_reset(self):
        """Loads the default settings into the UI for preview."""

        log.info("Resetting form to default values.")
        self._load_config_into_ui(self._defaults)

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
