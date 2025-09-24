"""
Бэкенд для Airspy через airspy_rx (бинарный вывод).
Вывод: бинарные данные IQ, но мы преобразуем их в PSD (по аналогии с qspectrumanalyzer).
Примечание: airspy_rx не имеет встроенного sweep, поэтому сканируем по одной частоте.
Для сканирования диапазона потребуется несколько вызовов (реализовано в основном потоке).
Это ограничение — такова особенность утилиты.
"""

import struct
import numpy as np
from PyQt5.QtCore import QProcess
from .base import BackendInfo, BackendPowerThread

class AirspyRxInfo(BackendInfo):
    cmd = "airspy_rx"
    args_template = [
        "-f", "{start}e6",
        "-s", "2500000",
        "-r", "/dev/stdout",
        "-g", "{gain}"
    ]
    hint_range = (24, 1800)
    hint_step = "Фикс. 2.5 МГц"
    default_gain = 15
    output_type = "binary"

    @classmethod
    def help_device(cls, executable: str, device: str) -> str:
        return (
            "Требуется Airspy Mini или Airspy R2.\n"
            "Установите драйверы airspyhf и airspy.\n"
            "Командная строка использует фиксированную ширину полосы 2.5 МГц."
        )

class AirspyRxThread(BackendPowerThread):
    def __init__(self, *args, **kwargs):
        super().__init__(AirspyRxInfo(), *args, **kwargs)
        self.buffer_bin = b""
        self.sample_rate = 2.5e6  # Фиксировано airspy_rx

    def setup(self):
        self.params = {
            "start": self.start_freq,
            "end": self.end_freq,
            "step": self.step,
            "gain": self.gain,
        }

    def process_start(self):
        """Запускаем airspy_rx."""
        args = [arg.format(**self.params) for arg in self.info.args_template]
        self.process = QProcess()
        self.process.setProgram(self.info.cmd)
        self.process.setArguments(args)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.start()
        if not self.process.waitForStarted(5000):
            raise RuntimeError(f"Не удалось запустить {self.info.cmd}")

    def parse_output(self, chunk: bytes):
        """Обрабатываем бинарный поток IQ данных и вычисляем спектр."""
        self.buffer_bin += chunk

        # Мы получаем IQ в формате float32 (4 байта на I, 4 байта на Q)
        # Полный блок должен быть кратен 8 байтам (I+Q)
        if len(self.buffer_bin) < 8:
            return

        # Обрабатываем как можно больше полных блоков
        n_samples = len(self.buffer_bin) // 8
        if n_samples == 0:
            return

        # Извлекаем IQ данные
        iq_data = np.frombuffer(self.buffer_bin[:n_samples*8], dtype=np.float32)
        # Разделяем на I и Q
        i_data = iq_data[::2]
        q_data = iq_data[1::2]
        # Собираем комплексные значения
        complex_data = i_data + 1j * q_data

        # Вычисляем FFT
        window = np.hanning(len(complex_data))
        fft_data = np.fft.fft(complex_data * window)
        power = 10 * np.log10(np.abs(fft_data)**2 + 1e-10)  # в dB

        # Вычисляем частоты
        center_freq = self.start_freq * 1e6
        freqs = np.linspace(center_freq - self.sample_rate/2, center_freq + self.sample_rate/2, len(power)) / 1e6  # в МГц

        # Эмитируем один снимок
        self.data_updated.emit({
            'x': freqs,
            'y': power,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        # Очищаем буфер
        self.buffer_bin = self.buffer_bin[n_samples*8:]
