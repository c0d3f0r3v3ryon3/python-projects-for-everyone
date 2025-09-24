"""
Таблица обнаруженных сигналов.
Отображает частоты, амплитуды, типы модуляции.
"""

import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QDoubleSpinBox, QPushButton
from PyQt5.QtCore import Qt
import numpy as np

class PeaksTableWidget(QWidget):
    def __init__(self, classifier, parent=None):
        super().__init__(parent)
        self.classifier = classifier
        self.peaks_df = None

        layout = QVBoxLayout()

        # Фильтры
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Мин. амплитуда (дБ):"))
        self.min_amp_spin = QDoubleSpinBox()
        self.min_amp_spin.setRange(-100, 0)
        self.min_amp_spin.setValue(-50)
        self.min_amp_spin.valueChanged.connect(self.update_display)
        filter_layout.addWidget(self.min_amp_spin)

        filter_layout.addWidget(QLabel("Мин. ширина (МГц):"))
        self.min_width_spin = QDoubleSpinBox()
        self.min_width_spin.setRange(0.001, 10)
        self.min_width_spin.setValue(0.01)
        self.min_width_spin.valueChanged.connect(self.update_display)
        filter_layout.addWidget(self.min_width_spin)

        layout.addLayout(filter_layout)

        # Таблица
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(7)
        self.table_widget.setHorizontalHeaderLabels([
            "Частота (МГц)", "Амплитуда (дБ)", "Левая гр.", "Правая гр.", "Ширина (МГц)", "Модуляция", "Тип"
        ])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, 1)  # Растягиваем по содержимому
        self.table_widget.horizontalHeader().setSectionResizeMode(1, 1)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, 1)
        self.table_widget.horizontalHeader().setSectionResizeMode(3, 1)
        self.table_widget.horizontalHeader().setSectionResizeMode(4, 1)
        self.table_widget.horizontalHeader().setSectionResizeMode(5, 1)
        self.table_widget.horizontalHeader().setSectionResizeMode(6, 1)
        self.table_widget.cellDoubleClicked.connect(self.on_peak_double_click)
        layout.addWidget(self.table_widget)

        # Кнопка "Пересчитать"
        self.recalc_button = QPushButton("🔄 Пересчитать")
        self.recalc_button.clicked.connect(self.update_display)
        layout.addWidget(self.recalc_button)

        self.setLayout(layout)

    def update_table(self, peak_list: list):
        """Обновить таблицу на основе списка пиков."""
        self.peaks_df = peak_list
        self.update_display()

    def update_display(self):
        """Применить фильтры и обновить таблицу."""
        if not self.peaks_df:
            self.table_widget.setRowCount(0)
            return

        filtered = [
            p for p in self.peaks_df
            if p["Амплитуда (дБ)"] >= self.min_amp_spin.value() and
               p["Ширина (МГц)"] >= self.min_width_spin.value()
        ]

        self.table_widget.setRowCount(len(filtered))
        for row, peak in enumerate(filtered):
            for col, key in enumerate([
                "Частота (МГц)", "Амплитуда (дБ)", "Левая гр.", "Правая гр.",
                "Ширина (МГц)", "Модуляция", "Тип"
            ]):
                value = peak[key]
                text = f"{value:.3f}" if isinstance(value, float) else str(value)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.table_widget.setItem(row, col, item)

    def on_peak_double_click(self, row, col):
        """Обработка двойного клика по пике."""
        freq_item = self.table_widget.item(row, 0)
        if freq_item:
            freq = freq_item.text()
            # Можно добавить логику переключения на эту частоту
            print(f"Двойной клик на пике: {freq} МГц")
