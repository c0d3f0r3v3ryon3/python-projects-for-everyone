"""
Диалог настройки сглаживания.
Аналог qspectrumanalyzer.QSpectrumAnalyzerSmoothing.
"""

from PyQt5.QtWidgets import QDialog, QComboBox, QSpinBox, QFormLayout, QDialogButtonBox
from PyQt5.QtCore import Qt

class SmoothingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сглаживание — SpectrumAnalyzer Pro v3.0")
        self.resize(250, 130)

        layout = QFormLayout()

        self.window_func_combo = QComboBox()
        self.window_func_combo.addItems(["rectangular", "hanning", "hamming", "bartlett", "blackman"])
        layout.addRow("&Функция окна:", self.window_func_combo)

        self.length_spin = QSpinBox()
        self.length_spin.setRange(3, 101)
        self.length_spin.setValue(11)
        layout.addRow("&Длина окна:", self.length_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        # Загрузка настроек
        self.load_settings()

    def load_settings(self):
        settings = self.parent().settings
        self.window_func_combo.setCurrentText(settings.value("smooth_window", "hanning"))
        self.length_spin.setValue(settings.value("smooth_length", 11, int))

    def accept(self):
        settings = self.parent().settings
        settings.setValue("smooth_window", self.window_func_combo.currentText())
        settings.setValue("smooth_length", self.length_spin.value())
        super().accept()
