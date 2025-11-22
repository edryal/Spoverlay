# pyright: reportGeneralTypeIssues=false
from typing import final, override
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox, QPushButton, QSpacerItem, QSizePolicy

from overlay.core.models import AppConfig, UIConfig
from overlay.core.config import get_default_config


@final
class ConfigureWindow(QWidget):
    config_saved = Signal(AppConfig)

    def __init__(self, config: AppConfig):
        super().__init__()
        self._current_config = config
        self._defaults = get_default_config()

        main_layout = QVBoxLayout(self)

        self.position_choice = QComboBox()
        self._add_widget_with_label(main_layout, self.position_choice, "Overlay Position:")
        self.position_choice.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])

        self.margin_spinbox = QSpinBox()
        self._add_widget_with_label(main_layout, self.margin_spinbox, "Screen Margin (px):")
        self.margin_spinbox.setRange(0, 500)

        self.art_size_spinbox = QSpinBox()
        self._add_widget_with_label(main_layout, self.art_size_spinbox, "Album Art Size (px):")
        self.art_size_spinbox.setRange(32, 256)
        self.art_size_spinbox.setSingleStep(8)

        self.poll_interval_spinbox = QSpinBox()
        self._add_widget_with_label(main_layout, self.poll_interval_spinbox, "Update Interval (ms):")
        self.poll_interval_spinbox.setRange(100, 5000)
        self.poll_interval_spinbox.setSingleStep(100)

        self.click_through_checkbox = QCheckBox("Overlay Click-Through")
        main_layout.addWidget(self.click_through_checkbox)

        self._load_config_into_ui()

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        button_layout = QHBoxLayout()
        reset_button = QPushButton("Reset to Default")
        _ = reset_button.clicked.connect(self._on_reset)

        save_button = QPushButton("Save & Apply")
        _ = save_button.clicked.connect(self._on_save)
        save_button.setDefault(True)

        close_button = QPushButton("Cancel")
        _ = close_button.clicked.connect(self.close)

        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addWidget(save_button)
        main_layout.addLayout(button_layout)

        self._setup_window_flags()

    def _add_widget_with_label(self, layout: QVBoxLayout, widget: QWidget, label_text: str):
        hbox = QHBoxLayout()
        label = QLabel(label_text)
        hbox.addWidget(label)
        hbox.addWidget(widget)
        layout.addLayout(hbox)

    def _load_config_into_ui(self, source_config: AppConfig | None = None):
        config = source_config or self._current_config
        self.position_choice.setCurrentText(config.ui.position)
        self.margin_spinbox.setValue(config.ui.margin)
        self.art_size_spinbox.setValue(config.ui.art_size)
        self.click_through_checkbox.setChecked(config.ui.click_through)
        self.poll_interval_spinbox.setValue(config.poll_interval_ms)

    def _on_save(self):
        new_ui_config = UIConfig(
            position=self.position_choice.currentText(),
            margin=self.margin_spinbox.value(),
            click_through=self.click_through_checkbox.isChecked(),
            art_size=self.art_size_spinbox.value(),
        )
        self._current_config.ui = new_ui_config
        self._current_config.poll_interval_ms = self.poll_interval_spinbox.value()

        self.config_saved.emit(self._current_config)
        _ = self.close()

    def _on_reset(self):
        self._load_config_into_ui(self._defaults)

    @override
    def showEvent(self, event: QShowEvent):
        self._load_config_into_ui()
        super().showEvent(event)

    def _setup_window_flags(self):
        self.setWindowTitle("Configure Spoverlay")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 250)
