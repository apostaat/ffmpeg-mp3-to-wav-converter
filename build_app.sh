#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Audio Converter"
DIST_DIR="dist"
APP_BUNDLE="${DIST_DIR}/${APP_NAME}.app"
DMG_NAME="404mk2wav.dmg"
ICON_PNG="logo.png"
ICON_ICNS="logo.icns"
FFMPEG_DIR="ffmpeg_bin"

# Проверяем наличие необходимых инструментов
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 не установлен"
    exit 1
fi

if ! command -v pip3 &>/dev/null; then
    echo "❌ pip3 не установлен"
    exit 1
fi

# Создаем виртуальное окружение
echo "🔧 Создаем виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
echo "📦 Устанавливаем зависимости..."
pip3 install -r requirements.txt
pip3 install pyinstaller pillow

# Скачиваем FFmpeg
echo "📥 Скачиваем FFmpeg..."
mkdir -p "${FFMPEG_DIR}"
curl -L "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip" -o ffmpeg.zip
unzip -q ffmpeg.zip -d "${FFMPEG_DIR}"
rm ffmpeg.zip

# Конвертируем иконку в ICNS формат
echo "🎨 Конвертируем иконку в ICNS формат..."
python3 -c "
from PIL import Image
import os

# Создаем временную директорию для иконок
os.makedirs('icon.iconset', exist_ok=True)

# Загружаем исходное изображение
img = Image.open('${ICON_PNG}')

# Создаем иконки разных размеров
sizes = [16, 32, 64, 128, 256, 512, 1024]
for size in sizes:
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(f'icon.iconset/icon_{size}x{size}.png')
    if size <= 512:  # Для ретина-дисплеев
        resized.save(f'icon.iconset/icon_{size//2}x{size//2}@2x.png')

# Конвертируем в ICNS
os.system('iconutil -c icns icon.iconset')
os.rename('icon.icns', '${ICON_ICNS}')

# Удаляем временные файлы
os.system('rm -rf icon.iconset')
"

# Создаем spec файл для PyInstaller
echo "📝 Создаем spec файл..."
cat > "${APP_NAME}.spec" << EOL
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')

a = Analysis(
    ['converter_app.py'],
    pathex=['.'],
    binaries=[('${FFMPEG_DIR}/ffmpeg', '.')] + pyqt6_binaries,  # Include FFmpeg binary
    datas=pyqt6_datas,
    hiddenimports=pyqt6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='${APP_NAME}',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='${ICON_ICNS}'
)

app = BUNDLE(
    exe,
    name='${APP_NAME}.app',
    icon='${ICON_ICNS}',
    bundle_identifier='com.audioconverter.app',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)
EOL

# Собираем приложение
echo "🔨 Собираем приложение..."
pyinstaller "${APP_NAME}.spec"

# Переносим .app в отдельную папку для DMG
echo "📦 Готовим папку для DMG..."
mkdir -p "${DIST_DIR}/dmg_content"
cp -R "${DIST_DIR}/${APP_NAME}.app" "${DIST_DIR}/dmg_content/"

# Создаем DMG
if command -v create-dmg &>/dev/null; then
    echo "💿 Создаем DMG через create-dmg..."
    create-dmg --volname "${APP_NAME}" --window-pos 200 120 --window-size 800 400 --icon-size 100 --app-drop-link 600 200 "${DIST_DIR}/${DMG_NAME}" "${DIST_DIR}/dmg_content/"
else
    echo "💿 Создаем DMG через hdiutil..."
    hdiutil create -volname "${APP_NAME}" -srcfolder "${DIST_DIR}/dmg_content" -ov -format UDZO "${DIST_DIR}/${DMG_NAME}"
fi

echo "✅ DMG-файл создан: ${DIST_DIR}/${DMG_NAME}"

# Создаем скрипт для запуска приложения с выводом ошибок
echo "📝 Создаем скрипт для отладки..."
cat > "debug_app.sh" << EOL
#!/bin/bash
"${DIST_DIR}/${APP_NAME}.app/Contents/MacOS/${APP_NAME}" 2>&1 | tee debug.log
EOL

chmod +x debug_app.sh

echo "🔍 Для отладки запустите: ./debug_app.sh"

# Очистка
echo "🧹 Очистка временных файлов..."
rm -rf "${FFMPEG_DIR}" 
