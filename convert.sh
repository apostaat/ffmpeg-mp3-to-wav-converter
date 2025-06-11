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
# Функция для транслитерации и очистки имени файла
# ------------------------
sanitize_filename() {
  local filename="$1"
  # Транслитерация кириллицы в латиницу
  filename=$(echo "$filename" | iconv -f utf-8 -t ascii//TRANSLIT)
  # Удаление специальных символов, оставляем только буквы, цифры, точки и дефисы
  filename=$(echo "$filename" | sed 's/[^a-zA-Z0-9.-]//g')
  # Заменяем множественные дефисы на один
  filename=$(echo "$filename" | sed 's/--*/-/g')
  # Удаляем дефисы в начале и конце
  filename=$(echo "$filename" | sed 's/^-//;s/-$//')
  echo "$filename"
}

# ------------------------
# Конвертация аудио → wav
# ------------------------
echo "🎧 Конвертация аудио файлов в WAV (44.1 kHz)"

# Поддерживаемые форматы
AUDIO_EXTENSIONS=("mp3" "wav" "aac" "m4a" "flac" "ogg" "wma" "aiff" "alac")

count=0
for ext in "${AUDIO_EXTENSIONS[@]}"; do
  while IFS= read -r -d '' audiofile; do
    # Получаем имя файла без расширения
    filename="${audiofile%.*}"
    # Получаем расширение файла
    fileext="${audiofile##*.}"
    
    # Пропускаем файлы, которые уже являются WAV
    if [[ "$fileext" == "wav" ]]; then
      continue
    fi
    
    # Создаем новое имя файла
    new_filename=$(sanitize_filename "$filename")
    wavfile="${new_filename}.wav"
    
    # Если файл с таким именем уже существует, добавляем числовой суффикс
    counter=1
    while [ -f "$wavfile" ]; do
      wavfile="${new_filename}_${counter}.wav"
      counter=$((counter + 1))
    done

    if "$FFMPEG_CMD" -loglevel error -y -i "$audiofile" -ar 44100 "$wavfile"; then
      echo "✅ $audiofile → $wavfile"
      rm "$audiofile"
      count=$((count + 1))
    else
      echo "❌ Ошибка при конвертации: $audiofile"
    fi
  done < <(find . -type f -iname "*.${ext}" -print0)
done

echo "🎉 Готово! Конвертировано файлов: $count"
