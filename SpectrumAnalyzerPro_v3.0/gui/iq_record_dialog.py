"""
Диалог записи IQ-данных.
Аналог вашего record_iq_signal, но как полноценный диалог.
"""

from PyQt5.QtWidgets import QDialog, QDoubleSpinBox, QSpinBox, QFormLayout, QDialogButtonBox, QFileDialog, QLineEdit
from PyQt5.QtCore import Qt

class IQRecordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Запись IQ-сигнала")
        self.resize(400, 200)

        layout = QFormLayout()

        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(1, 6000)
        self.freq_spin.setValue(100)
        self.freq_spin.setSuffix(" МГц")
        layout.addRow("Частота:", self.freq_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 3600)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" сек")
        layout.addRow("Длительность:", self.duration_spin)

        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(200000, 10000000)
        self.sample_rate_spin.setValue(2400000)
        self.sample_rate_spin.setSuffix(" Гц")
        layout.addRow("Частота дискретизации:", self.sample_rate_spin)

        self.filename_edit = QLineEdit()
        self.filename_button = QToolButton()
        self.filename_button.setText("...")
        self.filename_button.clicked.connect(self.select_filename)
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(self.filename_edit)
        filename_layout.addWidget(self.filename_button)
        layout.addRow("Файл сохранения:", filename_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        # Загрузка настроек
        self.load_settings()

    def load_settings(self):
        pass  # В данном случае нет сохраняемых настроек

    def select_filename(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить IQ файл", "", "Binary Files (*.bin);;WAV Files (*.wav)")
        if path:
            self.filename_edit.setText(path)

    def accept(self):
        self.parent().record_iq_signal(
            freq=self.freq_spin.value(),
            duration=self.duration_spin.value(),
            sample_rate=self.sample_rate_spin.value(),
            filename=self.filename_edit.text()
        )
        super().accept()
