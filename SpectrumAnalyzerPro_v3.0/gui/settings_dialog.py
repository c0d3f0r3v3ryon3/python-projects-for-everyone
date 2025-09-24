"""
Диалог настроек (аналог qspectrumanalyzer.QSpectrumAnalyzerSettings).
Поддерживает выбор бэкенда, параметры устройства, LNB LO, дополнительные параметры.
"""

import os
from PyQt5.QtWidgets import QDialog, QComboBox, QLineEdit, QToolButton, QFileDialog, QDoubleSpinBox, QSpinBox, QFormLayout, QDialogButtonBox, QMessageBox, QHBoxLayout, QHBoxLayout  # <-- ДОБАВЛЕНО!
from PyQt5.QtCore import Qt, pyqtSlot
from config import DEVICE_BACKENDS, SOAPY_DEVICES
from backend import RtlPowerInfo, HackRFSweepInfo, AirspyRxInfo, SoapyPowerInfo

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки — SpectrumAnalyzer Pro v3.0")
        self.resize(700, 500)
        layout = QFormLayout()

        # Backend
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(list(DEVICE_BACKENDS.keys()))
        layout.addRow("&Backend:", self.backend_combo)

        # Executable
        self.executable_edit = QLineEdit()
        self.executable_button = QToolButton()
        self.executable_button.setText("...")
        self.executable_button.clicked.connect(self.select_executable)
        exec_layout = QHBoxLayout()
        exec_layout.addWidget(self.executable_edit)
        exec_layout.addWidget(self.executable_button)
        layout.addRow("&Executable:", exec_layout)

        # Device (для SoapySDR)
        self.device_label = QLabel("&Device:")
        self.device_combo = QComboBox()
        self.device_combo.addItems(SOAPY_DEVICES)
        self.device_combo.setEnabled(False)
        layout.addRow(self.device_label, self.device_combo)

        # Sample Rate
        self.sample_rate_spin = QDoubleSpinBox()
        self.sample_rate_spin.setRange(0.1, 100)
        self.sample_rate_spin.setSuffix(" MHz")
        self.sample_rate_spin.setDecimals(3)
        layout.addRow("&Sample rate:", self.sample_rate_spin)

        # Bandwidth
        self.bandwidth_spin = QDoubleSpinBox()
        self.bandwidth_spin.setRange(0, 100)
        self.bandwidth_spin.setSuffix(" MHz")
        self.bandwidth_spin.setDecimals(3)
        layout.addRow("&Bandwidth:", self.bandwidth_spin)

        # LNB LO
        self.lnb_spin = QDoubleSpinBox()
        self.lnb_spin.setRange(-999, 999)
        self.lnb_spin.setSuffix(" MHz")
        self.lnb_spin.setDecimals(3)
        self.lnb_spin.setToolTip("Negative frequency for upconverters, positive frequency for downconverters.")
        layout.addRow("&LNB LO:", self.lnb_spin)

        # Additional params
        self.params_edit = QLineEdit()
        self.params_help_button = QToolButton()
        self.params_help_button.setText("?")
        self.params_help_button.clicked.connect(self.show_params_help)
        params_layout = QHBoxLayout()
        params_layout.addWidget(self.params_edit)
        params_layout.addWidget(self.params_help_button)
        layout.addRow("&Additional parameters:", params_layout)

        # Waterfall history size
        self.waterfall_history_spin = QSpinBox()
        self.waterfall_history_spin.setRange(10, 1000)
        self.waterfall_history_spin.setValue(100)
        layout.addRow("&Waterfall history size:", self.waterfall_history_spin)

        # Button box
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        # Загрузка настроек (оставьте как есть — это комментарии)
        self.load_settings()
        self.backend_combo.currentTextChanged.connect(self.on_backend_changed)

    def load_settings(self):
        settings = self.parent().settings
        backend = settings.value("backend", "soapy_power")
        index = self.backend_combo.findText(backend)
        if index >= 0:
            self.backend_combo.setCurrentIndex(index)
        self.executable_edit.setText(settings.value("executable", ""))
        self.device_combo.setCurrentText(settings.value("device", ""))
        self.sample_rate_spin.setValue(settings.value("sample_rate", 2.56, float))
        self.bandwidth_spin.setValue(settings.value("bandwidth", 0.0, float))
        self.lnb_spin.setValue(settings.value("lnb_lo", 0.0, float))
        self.params_edit.setText(settings.value("params", ""))
        self.waterfall_history_spin.setValue(settings.value("waterfall_history_size", 100, int))

    def save_settings(self):
        settings = self.parent().settings
        settings.setValue("backend", self.backend_combo.currentText())
        settings.setValue("executable", self.executable_edit.text())
        settings.setValue("device", self.device_combo.currentText())
        settings.setValue("sample_rate", self.sample_rate_spin.value())
        settings.setValue("bandwidth", self.bandwidth_spin.value())
        settings.setValue("lnb_lo", self.lnb_spin.value())
        settings.setValue("params", self.params_edit.text())
        settings.setValue("waterfall_history_size", self.waterfall_history_spin.value())

    def on_backend_changed(self, backend_name):
        info_class = DEVICE_BACKENDS[backend_name][0]
        # Обновляем поля
        self.executable_edit.setText(info_class.cmd)
        self.sample_rate_spin.setValue(getattr(info_class, 'default_sample_rate', 2.56))
        self.bandwidth_spin.setValue(getattr(info_class, 'default_bandwidth', 0.0))
        self.params_edit.setText(info_class.get_additional_params() if hasattr(info_class, 'get_additional_params') else "")
        self.device_combo.setEnabled(backend_name == "soapy_power")

    def select_executable(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите исполняемый файл", "", "Executable Files (*)")
        if path:
            self.executable_edit.setText(path)

    def show_params_help(self):
        backend_name = self.backend_combo.currentText()
        info_class = DEVICE_BACKENDS[backend_name][0]
        help_text = info_class.get_help_device(info_class.cmd, self.device_combo.currentText()) if hasattr(info_class, 'get_help_device') else "Справка отсутствует."
        QMessageBox.information(self, "Помощь по параметрам", help_text)

    def accept(self):
        self.save_settings()
        super().accept()
