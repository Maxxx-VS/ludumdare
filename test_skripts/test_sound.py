#!/usr/bin/env python3
"""
Скрипт записи 3 секунд с USB-микрофона и воспроизведения через USB-динамик
Оптимизирован для Jetson Orin NX.
"""

import sys
import subprocess

# Проверка и установка необходимых библиотек
try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("Устанавливаю необходимые библиотеки: sounddevice, numpy...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sounddevice", "numpy"])
    import sounddevice as sd
    import numpy as np
    print("Установка завершена.\n")


def find_device_by_name(name_substring, kind='output'):
    """Возвращает индекс устройства по подстроке имени."""
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if name_substring.lower() in dev['name'].lower():
            if kind == 'input' and dev['max_input_channels'] > 0:
                return idx
            elif kind == 'output' and dev['max_output_channels'] > 0:
                return idx
    return None


def main():
    # Поиск устройств
    mic_idx = find_device_by_name("AB13X USB Audio", kind='input')
    speaker_idx = find_device_by_name("UACDemoV1.0", kind='output')

    if mic_idx is None or speaker_idx is None:
        print("Не найдены необходимые устройства!")
        sys.exit(1)

    mic_info = sd.query_devices(mic_idx)
    speaker_info = sd.query_devices(speaker_idx)

    print(f"🎤 Микрофон : {mic_info['name']}")
    print(f"🔊 Динамик  : {speaker_info['name']}")

    # Параметры записи
    DURATION = 3.0
    SAMPLE_RATE = 48000      # <-- изменено на 48000 Гц
    CHANNELS = 1

    print(f"\n⏺️  Запись {DURATION} секунд (частота {SAMPLE_RATE} Гц)... Говорите в микрофон")
    try:
        recording = sd.rec(
            int(DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            device=mic_idx,
            dtype='int16'      # явно указываем 16-бит, чтобы избежать преобразований
        )
        sd.wait()
        print("✅ Запись завершена.")
    except Exception as e:
        print(f"❌ Ошибка при записи: {e}")
        sys.exit(1)

    print("⏯️  Воспроизведение записи через USB-динамик...")
    try:
        sd.play(recording, samplerate=SAMPLE_RATE, device=speaker_idx)
        sd.wait()
        print("✅ Воспроизведение завершено.")
    except Exception as e:
        print(f"❌ Ошибка при воспроизведении: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
