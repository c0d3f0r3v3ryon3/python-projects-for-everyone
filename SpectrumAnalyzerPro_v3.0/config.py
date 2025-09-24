"""
Определение всех поддерживаемых устройств и их параметров.
Аналогично qspectrumanalyzer.backends, но адаптировано под ваш стиль.
"""

DEVICE_BACKENDS = {
    "rtl_power": {
        "cmd": "rtl_power",
        "args_template": [
            "-f", "{start}M:{end}M:{step}k",
            "-i", "{interval}",
            "-g", "{gain}",
            "-1", "-"
        ],
        "hint_range": (24, 1766),
        "hint_step": "1–2500 кГц",
        "default_gain": 30,
        "output_type": "text",
        "module": "backend.rtl_power"
    },
    "hackrf_sweep": {
        "cmd": "hackrf_sweep",
        "args_template": [
            "-f", "{start}:{end}",
            "-w", "{step}000",
            "-g", "{gain}",
            "-l", "{lna_gain}"
        ],
        "hint_range": (0, 7250),
        "hint_step": "100–5000 кГц",
        "default_gain": 20,
        "lna_gain_default": 16,
        "output_type": "binary",
        "module": "backend.hackrf_sweep"
    },
    "airspy_rx": {
        "cmd": "airspy_rx",
        "args_template": [
            "-f", "{start}e6",
            "-s", "2500000",
            "-r", "/dev/stdout",
            "-g", "{gain}"
        ],
        "hint_range": (24, 1800),
        "hint_step": "Фикс. 2.5 МГц",
        "default_gain": 15,
        "output_type": "binary",
        "module": "backend.airspy_rx"
    },
    "soapy_power": {
        "cmd": "soapy_power",
        "args_template": [
            "-f", "{start}M:{end}M",
            "-B", "{step}k",
            "-T", "{interval}",
            "-d", "{device}",
            "-r", "{sample_rate}",
            "-p", "{ppm}",
            "-F", "soapy_power_bin",
            "--output-fd", "{fd}"
        ],
        "hint_range": (0, 7250),
        "hint_step": "1–5000 кГц",
        "default_gain": 20,
        "default_sample_rate": 2560000,
        "default_ppm": 0,
        "output_type": "binary",
        "module": "backend.soapy_power"
    }
}

# Дополнительные параметры по умолчанию (для soapy_power)
SOAPY_POWER_DEFAULT_PARAMS = "--even --fft-window boxcar --remove-dc"

# Поддерживаемые устройства для SoapySDR (отображаются в dropdown)
SOAPY_DEVICES = [
    "RTL-SDR",
    "HackRF",
    "Airspy",
    "SDRplay",
    "LimeSDR",
    "PlutoSDR",
    "BladeRF"
]
