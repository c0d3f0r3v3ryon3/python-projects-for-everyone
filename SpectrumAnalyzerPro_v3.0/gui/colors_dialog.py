"""
Диалог настройки цветов графиков.
Аналог qspectrumanalyzer.QSpectrumAnalyzerColors.
"""

from PyQt5.QtWidgets import QDialog, QColorDialog, QPushButton, QFormLayout, QDialogButtonBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

class ColorsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Цвета — SpectrumAnalyzer Pro v3.0")
        self.resize(300, 300)

        layout = QFormLayout()

        self.main_color_btn = QPushButton("Цвет основной линии")
        self.peak_max_color_btn = QPushButton("Цвет пик-холд макс")
        self.peak_min_color_btn = QPushButton("Цвет пик-холд мин")
        self.average_color_btn = QPushButton("Цвет среднего")
        self.persistence_color_btn = QPushButton("Цвет персистентности")
        self.baseline_color_btn = QPushButton("Цвет базовой линии")

        self.main_color = QColor(0, 255, 255)   # Cyan
        self.peak_max_color = QColor(255, 0, 0) # Red
        self.peak_min_color = QColor(0, 0, 255) # Blue
        self.average_color = QColor(0, 255, 255) # Cyan
        self.persistence_color = QColor(0, 255, 0) # Green
        self.baseline_color = QColor(255, 0, 255) # Magenta

        self.main_color_btn.clicked.connect(lambda: self.choose_color('main'))
        self.peak_max_color_btn.clicked.connect(lambda: self.choose_color('peak_max'))
        self.peak_min_color_btn.clicked.connect(lambda: self.choose_color('peak_min'))
        self.average_color_btn.clicked.connect(lambda: self.choose_color('average'))
        self.persistence_color_btn.clicked.connect(lambda: self.choose_color('persistence'))
        self.baseline_color_btn.clicked.connect(lambda: self.choose_color('baseline'))

        layout.addRow(self.main_color_btn)
        layout.addRow(self.peak_max_color_btn)
        layout.addRow(self.peak_min_color_btn)
        layout.addRow(self.average_color_btn)
        layout.addRow(self.persistence_color_btn)
        layout.addRow(self.baseline_color_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def choose_color(self, name):
        color = QColorDialog.getColor(getattr(self, f"{name}_color"), self, f"Выберите цвет для {name}")
        if color.isValid():
            setattr(self, f"{name}_color", color)

    def accept(self):
        self.parent().settings.setValue("main_color", self.main_color.name())
        self.parent().settings.setValue("peak_hold_max_color", self.peak_max_color.name())
        self.parent().settings.setValue("peak_hold_min_color", self.peak_min_color.name())
        self.parent().settings.setValue("average_color", self.average_color.name())
        self.parent().settings.setValue("persistence_color", self.persistence_color.name())
        self.parent().settings.setValue("baseline_color", self.baseline_color.name())
        super().accept()
