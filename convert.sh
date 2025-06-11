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
transliterate() {
  local text="$1"
  
  # Транслитерация кириллицы в латиницу
  text=$(echo "$text" | sed '
    # строчные
    y/абвгдеёжзийклмнопрстуфхцчшщъыьэюя/abvgdeejzijklmnoprstufhzcss_y_eua/
    # заглавные
    y/АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ/ABVGDEEJZIJKLMNOPRSTUFHZCSS_Y_EUA/
  ')
  
  echo "$text"
}

sanitize_filename() {
  local filename="$1"
  
  # Транслитерация кириллицы
  filename=$(transliterate "$filename")
  
  # Удаляем все специальные символы, оставляем только буквы и цифры
  filename=$(echo "$filename" | sed 's/[^a-zA-Z0-9]//g')
  
  # Если имя файла пустое после всех преобразований, используем "untitled"
  if [ -z "$filename" ]; then
    filename="untitled"
  fi
  
  # Приводим к нижнему регистру
  filename=$(echo "$filename" | tr '[:upper:]' '[:lower:]')
  
  echo "$filename"
}

# ------------------------
# Конвертация аудио → wav
# ------------------------
echo "🎧 Конвертация аудио файлов в WAV (44.1 kHz)"

# Поддерживаемые форматы
AUDIO_EXTENSIONS=("mp3" "wav" "aac" "m4a" "flac" "ogg" "wma" "aiff" "alac")

count=0
errors=0

for ext in "${AUDIO_EXTENSIONS[@]}"; do
  while IFS= read -r -d '' audiofile; do
    # Проверяем существование файла
    if [ ! -f "$audiofile" ]; then
      echo "❌ Файл не найден: $audiofile"
      errors=$((errors + 1))
      continue
    fi

    # Получаем директорию и имя файла
    dirpath=$(dirname "$audiofile")
    filename=$(basename "$audiofile")
    fileext="${filename##*.}"
    
    # Пропускаем файлы, которые уже являются WAV
    if [[ "$fileext" == "wav" ]]; then
      continue
    fi
    
    # Создаем новое имя файла
    new_filename=$(sanitize_filename "${filename%.*}")
    wavfile="${dirpath}/${new_filename}.wav"
    
    # Если файл с таким именем уже существует, добавляем числовой суффикс
    counter=1
    while [ -f "$wavfile" ]; do
      if [ "$new_filename" = "untitled" ]; then
        wavfile="${dirpath}/untitled${counter}.wav"
      else
        wavfile="${dirpath}/${new_filename}_${counter}.wav"
      fi
      counter=$((counter + 1))
    done

    echo "🔄 Конвертация: $audiofile"
    echo "📝 Новое имя: $wavfile"

    # Конвертируем файл с подробным выводом ошибок
    if "$FFMPEG_CMD" -loglevel warning -y -i "$audiofile" -ar 44100 "$wavfile" 2> >(tee -a conversion_errors.log >&2); then
      # Проверяем, что выходной файл существует и не пустой
      if [ -s "$wavfile" ]; then
        echo "✅ Успешно: $audiofile → $wavfile"
        rm "$audiofile"
        count=$((count + 1))
      else
        echo "❌ Ошибка: выходной файл пустой или не создан: $wavfile"
        errors=$((errors + 1))
        # Удаляем пустой выходной файл
        rm -f "$wavfile"
      fi
    else
      echo "❌ Ошибка при конвертации: $audiofile"
      errors=$((errors + 1))
    fi
  done < <(find . -type f -iname "*.${ext}" -print0)
done

echo "🎉 Готово! Конвертировано файлов: $count"
if [ $errors -gt 0 ]; then
  echo "⚠️  Количество ошибок: $errors"
  echo "📋 Подробности ошибок сохранены в файле: conversion_errors.log"
fi
