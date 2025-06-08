#!/usr/bin/env bash
# convert.sh — автоконвертер mp3→wav с установкой ffmpeg (с GitHub)

set -euo pipefail

# ---------------------------------------------------------
# 1. Установка ffmpeg из исходников, если не установлен
# ---------------------------------------------------------
if ! command -v ffmpeg &>/dev/null; then
  echo "⚙️ ffmpeg не найден → собираем из исходников..."
  xcode-select --install 2>/dev/null || true
  cd "$(mktemp -d)"
  git clone https://github.com/FFmpeg/FFmpeg.git ffmpeg-src
  cd ffmpeg-src
  ./configure --disable-debug --disable-doc --disable-ffplay --enable-shared
  make -j"$(sysctl -n hw.logicalcpu)"
  sudo make install
  echo "✅ ffmpeg установлен"
fi

# ---------------------------------------------------------
# 2. Конвертация mp3 → wav + удаление + подсчёт
# ---------------------------------------------------------
count=0
while IFS= read -r mp3file; do
  wavfile="${mp3file%.mp3}.wav"
  ffmpeg -loglevel error -y -i "$mp3file" -ar 44100 "$wavfile" \
    && echo "✅ Сконвертирован: $mp3file → $wavfile" \
    && ((count++)) \
    && rm "$mp3file" \
    && echo "🗑️ Удалён: $mp3file" \
    || echo "❌ Ошибка: $mp3file"
done < <(find . -type f -iname "*.mp3")

echo "🔚 Всего сконвертировано файлов: $count"
