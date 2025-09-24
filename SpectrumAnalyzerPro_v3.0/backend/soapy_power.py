"""
Backend для SoapySDR через soapy_power (бинарный формат).
Используется для RTL-SDR, HackRF, Airspy, LimeSDR, PlutoSDR и т.д.
"""

import os
import struct
import numpy as np
from PyQt5.QtCore import QProcess
from .base import BackendInfo, BackendPowerThread
from utils.logger import get_logger

logger = get_logger(__name__)

class SoapyPowerInfo(BackendInfo):
    cmd = "soapy_power"
    args_template = [
        "-f", "{start}M:{end}M",
        "-B", "{step}k",
        "-T", "{interval}",
        "-d", "{device}",
        "-r", "{sample_rate}",
        "-p", "{ppm}",
        "-F", "soapy_power_bin",
        "--output-fd", "{fd}"
    ]
    hint_range = (0, 7250)
    hint_step = "1–5000 кГц"
    default_gain = 20
    default_sample_rate = 2560000
    default_ppm = 0
    output_type = "binary"

    @classmethod
    def help_device(cls, executable: str, device: str) -> str:
        """Возвращает справку по устройству."""
        return (
            "Используйте SoapySDR для управления устройствами.\n"
            "Поддерживаемые устройства: RTL-SDR, HackRF, Airspy, SDRplay, LimeSDR, PlutoSDR, BladeRF.\n"
            "Установите драйверы через: sudo apt install soapysdr-module-<device>\n"
            "Настройте параметры: частота, усиление, PPM-коррекция."
        )

class SoapyPowerThread(BackendPowerThread):
    def __init__(self, *args, **kwargs):
        super().__init__(SoapyPowerInfo(), *args, **kwargs)
        self.pipe_read_fd = None
        self.pipe_write_fd = None
        self.pipe_read = None
        self.pipe_write_handle = None

    def setup(self):
        """Подготовить параметры для soapy_power."""
        self.params = {
            "start": self.start_freq,
            "end": self.end_freq,
            "step": self.step,
            "interval": self.interval,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "ppm": self.ppm,
            "fd": "0"  # placeholder for pipe
        }

    def process_start(self):
        """Запустить soapy_power с пайпом."""
        import tempfile
        import subprocess

        # Создаем pipe
        rpipe, wpipe = os.pipe()
        self.pipe_read_fd = rpipe
        self.pipe_write_fd = wpipe

        # Подготавливаем команду
        cmdline = [self.info.cmd]
        for arg in self.info.args_template:
            if "{fd}" in arg:
                cmdline.append(arg.format(fd=str(wpipe)))
            else:
                cmdline.append(arg.format(**self.params))

        # Добавляем дополнительные параметры
        from config import SOAPY_POWER_DEFAULT_PARAMS
        cmdline.extend(SOAPY_POWER_DEFAULT_PARAMS.split())

        logger.info(f"Запуск: {' '.join(cmdline)}")

        # Запускаем процесс
        self.process = QProcess()
        self.process.setProgram(cmdline[0])
        self.process.setArguments(cmdline[1:])
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.start()

        # Закрываем сторону записи
        os.close(wpipe)

        # Настраиваем чтение из pipe
        self.pipe_read = os.fdopen(rpipe, 'rb')

    def parse_output(self, buf: bytes):
        """Разбор бинарного формата soapy_power_bin."""
        try:
            # Структура заголовка: 8+8+8+8+4+4+4+4+4+4 = 60 байт
            # time_start, time_stop, start, stop, step, samples, flags, reserved, width, height
            header_size = 60
            if len(buf) < header_size:
                return

            header = struct.unpack('>QQQQIIIIII', buf[:header_size])
            time_start, time_stop, start_freq, stop_freq, step, samples, flags, _, width, height = header

            if len(buf) < header_size + samples * 4:
                return  # Не хватает данных

            y_data = np.frombuffer(buf[header_size:header_size + samples*4], dtype=np.float32)
            x_data = np.linspace(start_freq / 1e6, stop_freq / 1e6, len(y_data))  # в МГц

            # Применяем LNB LO
            if self.lnb_lo != 0:
                x_data += self.lnb_lo

            self.data_updated.emit({
                'x': x_data,
                'y': y_data,
                'timestamp': f"{time_start}.{time_stop}"
            })

        except Exception as e:
            logger.error(f"Ошибка парсинга soapy_power: {e}")
            return

    def process_stop(self):
        """Остановить процесс и закрыть pipe."""
        super().process_stop()
        if self.pipe_read:
            self.pipe_read.close()
        self.pipe_read_fd = None
        self.pipe_write_fd = None
        self.pipe_read = None
        self.pipe_write_handle = None
