"""
Диалог загрузки базовой линии.
Аналог qspectrumanalyzer.QSpectrumAnalyzerBaseline.
"""

import os
from PyQt5.QtWidgets import QDialog, QLineEdit, QToolButton, QFileDialog, QFormLayout, QDialogButtonBox

class BaselineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Базовая линия — SpectrumAnalyzer Pro v3.0")
        self.resize(500, 100)

        layout = QFormLayout()

        self.file_edit = QLineEdit()
        self.file_button = QToolButton()
        self.file_button.setText("...")
        self.file_button.clicked.connect(self.select_file)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(self.file_button)
        layout.addRow("&Файл базовой линии:", file_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        # Загрузка настроек
        self.load_settings()

    def load_settings(self):
        settings = self.parent().settings
        self.file_edit.setText(settings.value("baseline_file", ""))

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл базовой линии", "", "CSV Files (*.csv);;All Files (*)")
        if path:
            self.file_edit.setText(path)

    def accept(self):
        settings = self.parent().settings
        settings.setValue("baseline_file", self.file_edit.text())
        super().accept()
