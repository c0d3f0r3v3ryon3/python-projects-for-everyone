"""
Диалог настройки персистентности.
Аналог qspectrumanalyzer.QSpectrumAnalyzerPersistence.
"""

from PyQt5.QtWidgets import QDialog, QComboBox, QSpinBox, QFormLayout, QDialogButtonBox
from PyQt5.QtCore import Qt

class PersistenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Персистентность — SpectrumAnalyzer Pro v3.0")
        self.resize(250, 130)

        layout = QFormLayout()

        self.decay_combo = QComboBox()
        self.decay_combo.addItems(["linear", "exponential"])
        layout.addRow("Функция затухания:", self.decay_combo)

        self.length_spin = QSpinBox()
        self.length_spin.setRange(1, 20)
        self.length_spin.setValue(5)
        layout.addRow("Длина персистентности:", self.length_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        # Загрузка настроек
        self.load_settings()

    def load_settings(self):
        settings = self.parent().settings
        self.decay_combo.setCurrentText(settings.value("persistence_decay", "exponential"))
        self.length_spin.setValue(settings.value("persistence_length", 5, int))

    def accept(self):
        settings = self.parent().settings
        settings.setValue("persistence_decay", self.decay_combo.currentText())
        settings.setValue("persistence_length", self.length_spin.value())
        super().accept()
