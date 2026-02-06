# MP3 to WAV Converter for Roland SP404 MK2

<img width="267" height="56" alt="image" src="https://github.com/user-attachments/assets/12741a28-d5af-4824-9374-470dfa0882fe" />

A simple tool that converts all .mp3 files in a folder to 44.1 khz .wav format, preserving filenames, and then deletes the original .mp3 files.

## Features
- Converts MP3 files to WAV format (44.1 kHz)
- Preserves original filenames
- Automatically removes original MP3 files after conversion
- Installs all required dependencies automatically
- Works on macOS, Linux, and Windows

## Requirements

### macOS
- Homebrew (required for installing dependencies)
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

## Quick Start

1. Clone this repository:
```bash
git clone https://github.com/apostaat/ffmpeg-mp3-to-wav-converter.git
cd ffmpeg-mp3-to-wav-converter
```

2. Run the application:
```bash
make app
```

That's it! The application will:
- Install Python if needed
- Install ffmpeg if needed
- Install all required dependencies
- Launch the converter

## Alternative Installation Methods

### Using Shell Script
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/apostaat/ffmpeg-mp3-to-wav-converter/main/convert.sh)"
```

### Using Docker
```bash
make up
```

## Building Distributables

To create standalone applications for distribution:

### macOS .app Bundle
```bash
make build-dist
```
This will create a `dist/Audio Converter.app` bundle and a `dist/Audio Converter.dmg` installer.

### Windows .exe
```bash
make build-dist
```
This will create a `dist/Audio Converter.exe` executable and a `dist/Audio Converter_Windows.zip` archive.

### Manual Build
You can also run the build script directly:
```bash
python3 build_distributables.py
```

### Clean Build Artifacts
```bash
make clean-dist
```
