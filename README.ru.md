# Конвертер MP3 в WAV для Roland SP404 MK2

<img width="267" height="56" alt="image" src="https://github.com/user-attachments/assets/12741a28-d5af-4824-9374-470dfa0882fe" />

Простой инструмент, который конвертирует все `.mp3` файлы в выбранной папке в формат `.wav` 44.1 kHz, сохраняя имена файлов, а затем удаляет исходные `.mp3`.

## Возможности
- Конвертация MP3 в WAV (44.1 kHz)
- Сохранение исходных имён файлов
- Автоматическое удаление исходных MP3 после конвертации
- Автоматическая установка всех зависимостей
- Работает на macOS, Linux и Windows

## Требования

### macOS
- Homebrew (нужен для установки зависимостей)
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

### Linux
- Python 3
- pip3
- ffmpeg

### Windows
- Python 3
- pip3
- ffmpeg

## Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone https://github.com/apostaat/ffmpeg-mp3-to-wav-converter.git
cd ffmpeg-mp3-to-wav-converter
```

2. Запустите приложение:
```bash
make app
```

Готово! Приложение:
- установит Python при необходимости
- установит ffmpeg при необходимости
- установит все нужные зависимости
- запустит конвертер

## Альтернативные способы установки

### Через shell-скрипт
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/apostaat/ffmpeg-mp3-to-wav-converter/main/convert.sh)"
```

### Через Docker
```bash
make up
```

## Сборка дистрибутивов

Чтобы собрать автономные приложения для распространения:

### macOS .app Bundle
```bash
make build-dist
```
Это создаст `dist/Audio Converter.app` и установщик `dist/Audio Converter.dmg`.

### Windows .exe
```bash
make build-dist
```
Это создаст `dist/Audio Converter.exe` и архив `dist/Audio Converter_Windows.zip`.

### Ручная сборка
Можно запустить скрипт сборки напрямую:
```bash
python3 build_distributables.py
```

### Очистка артефактов сборки
```bash
make clean-dist
```
