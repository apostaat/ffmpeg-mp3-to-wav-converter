#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR="$HOME/ffmpeg_build"
PREFIX="$BUILD_DIR/install"

mkdir -p "$BUILD_DIR"
export PATH="$PREFIX/bin:$PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"

# ------------------------
# Проверка наличия ffmpeg
# ------------------------

# Проверяем наличие ffmpeg в системе
if command -v ffmpeg &>/dev/null; then
  FFMPEG_CMD="$(command -v ffmpeg)"
  echo "✅ Используем системный ffmpeg: $FFMPEG_CMD"
else
  echo "⚙️ ffmpeg не найден — устанавливаем..."
  
  if [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
    echo "🍺 Установка через Homebrew"
    brew install ffmpeg
    FFMPEG_CMD="$(command -v ffmpeg)"
  else
    echo "🔧 Сборка из исходников..."
    
    cd "$BUILD_DIR"
    
    # Установка NASM
    curl -LO https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/nasm-2.15.05.tar.gz
    tar xzvf nasm-2.15.05.tar.gz && cd nasm-2.15.05
    ./configure --prefix="$PREFIX" && make -j$(nproc || sysctl -n hw.logicalcpu) && make install
    cd ..
    
    # Сборка FFmpeg
    git clone --depth 1 https://github.com/FFmpeg/FFmpeg ffmpeg
    cd ffmpeg
    ./configure --prefix="$PREFIX" --disable-shared --enable-static
    make -j$(nproc || sysctl -n hw.logicalcpu) && make install
    cd ..
    
    FFMPEG_CMD="$PREFIX/bin/ffmpeg"
  fi
  
  if [ ! -x "$FFMPEG_CMD" ]; then
    echo "❌ Не удалось установить ffmpeg"
    exit 1
  fi
  
  echo "✅ ffmpeg успешно установлен: $FFMPEG_CMD"
fi

# ------------------------
# Конвертация mp3 → wav
# ------------------------
echo "🎧 Конвертация mp3 → wav"

count=0
while IFS= read -r -d '' mp3file; do
  wavfile="${mp3file%.mp3}.wav"

  if "$FFMPEG_CMD" -loglevel error -y -i "$mp3file" -ar 44100 "$wavfile"; then
    echo "✅ $mp3file → $wavfile"
    rm "$mp3file"
    count=$((count + 1))
  else
    echo "❌ Ошибка при конвертации: $mp3file"
  fi
done < <(find . -type f -iname "*.mp3" -print0)

echo "🎉 Готово! Конвертировано файлов: $count"
