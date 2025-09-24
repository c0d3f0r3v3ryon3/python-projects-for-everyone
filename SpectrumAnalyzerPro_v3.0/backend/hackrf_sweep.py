"""
Бэкенд для HackRF через hackrf_sweep (бинарный вывод).
Аналогично qspectrumanalyzer, но адаптировано под нашу структуру.
"""

import struct
import numpy as np
from PyQt5.QtCore import QProcess
from .base import BackendInfo, BackendPowerThread

class HackRFSweepInfo(BackendInfo):
    cmd = "hackrf_sweep"
    args_template = [
        "-f", "{start}:{end}",
        "-w", "{step}000",
        "-g", "{gain}",
        "-l", "{lna_gain}"
    ]
    hint_range = (0, 7250)
    hint_step = "100–5000 кГц"
    default_gain = 20
    lna_gain_default = 16
    output_type = "binary"

    @classmethod
    def help_device(cls, executable: str, device: str) -> str:
        return (
            "Требуется HackRF One или аналогичное устройство.\n"
            "Установите firmware через 'hackrf_info'.\n"
            "Режим sweep обеспечивает скорость до 8 ГГц/с."
        )

class HackRFSweepThread(BackendPowerThread):
    def __init__(self, *args, **kwargs):
        super().__init__(HackRFSweepInfo(), *args, **kwargs)
        self.buffer_bin = b""
        self.last_sweep_time = 0

    def setup(self):
        self.params = {
            "start": self.start_freq,
            "end": self.end_freq,
            "step": self.step,
            "gain": self.gain,
            "lna_gain": getattr(self, 'lna_gain', 16),
        }

    def process_start(self):
        """Запускаем hackrf_sweep."""
        args = [arg.format(**self.params) for arg in self.info.args_template]
        # Добавляем флаг -B для бинарного режима
        args.insert(1, "-B")
        self.process = QProcess()
        self.process.setProgram(self.info.cmd)
        self.process.setArguments(args)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.start()
        if not self.process.waitForStarted(5000):
            raise RuntimeError(f"Не удалось запустить {self.info.cmd}")

    def parse_output(self, chunk: bytes):
        """Парсим бинарный вывод hackrf_sweep."""
        self.buffer_bin += chunk

        while len(self.buffer_bin) >= 24:  # Минимальный заголовок: 8+8+8 = 24 байта
            header = self.buffer_bin[:24]
            try:
                low_edge, high_edge, record_length = struct.unpack('<QQI', header)
            except struct.error:
                break  # Недостаточно данных для заголовка

            if len(self.buffer_bin) < 24 + record_length:
                break  # Не хватает данных для всего пакета

            # Извлекаем данные RSSI
            data_bytes = self.buffer_bin[24:24 + record_length]
            count = record_length // 4  # Каждое значение — float32 (4 байта)
            rssi_data = struct.unpack(f'<{count}f', data_bytes)

            # Вычисляем частоты
            step = (high_edge - low_edge) / count
            frequencies = np.linspace(low_edge / 1e6, high_edge / 1e6, count)  # в МГц

            # Применяем LNB LO
            if self.lnb_lo != 0:
                frequencies += self.lnb_lo

            # Формируем массив мощностей
            db_values = np.array(rssi_data)

            # Эмитируем сигнал
            self.data_updated.emit({
                'x': frequencies,
                'y': db_values,
                'timestamp': f"{low_edge}-{high_edge}"
            })

            # Удаляем обработанные данные из буфера
            self.buffer_bin = self.buffer_bin[24 + record_length:]
