#!/usr/bin/env bash
# convert.sh — mp3→wav с установкой ffmpeg (через brew или сборкой из исходников)

set -euo pipefail

# Папка для исходников и сборки
BUILD_DIR="$HOME/ffmpeg_build"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

export PREFIX="$BUILD_DIR/install"
export PATH="$PREFIX/bin:$PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"

# ---------------------------------------------------------
# Проверка наличия ffmpeg
# ---------------------------------------------------------
if command -v ffmpeg &>/dev/null; then
  echo "✅ ffmpeg уже установлен: $(command -v ffmpeg)"
else
  echo "⚙️ ffmpeg не найден"

  # ---------------------------------------------------------
  # macOS + Homebrew: установка через brew
  # ---------------------------------------------------------
  if [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
    echo "🍺 macOS с установленным brew → устанавливаем ffmpeg через brew"
    brew install ffmpeg
    echo "✅ ffmpeg установлен через brew"
  else
    echo "🔧 Начинаем сборку ffmpeg и зависимостей из исходников..."

    build_nasm() {
      echo "📦 Сборка: nasm"
      curl -LO https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/nasm-2.15.05.tar.gz
      tar xzvf nasm-2.15.05.tar.gz
      cd nasm-2.15.05
      ./configure --prefix="$PREFIX" && make -j$(nproc || sysctl -n hw.logicalcpu) && make install
      cd ..
    }

    build_yasm() {
      echo "📦 Сборка: yasm"
      curl -LO https://www.tortall.net/projects/yasm/releases/yasm-1.3.0.tar.gz
      tar xzvf yasm-1.3.0.tar.gz
      cd yasm-1.3.0
      ./configure --prefix="$PREFIX" && make -j$(nproc || sysctl -n hw.logicalcpu) && make install
      cd ..
    }

    build_x264() {
      echo "📦 Сборка: x264"
      git clone https://code.videolan.org/videolan/x264.git
      cd x264
      ./configure --prefix="$PREFIX" --enable-static --disable-opencl
      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd ..
    }

    build_x265() {
      echo "📦 Сборка: x265"
      git clone https://bitbucket.org/multicoreware/x265_git.git x265
      cd x265/build/linux || cd x265/source
      cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$PREFIX" -DENABLE_SHARED=off ../../source
      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd "$BUILD_DIR"
    }

    build_libvpx() {
      echo "📦 Сборка: libvpx"
      git clone https://chromium.googlesource.com/webm/libvpx
      cd libvpx
      ./configure --prefix="$PREFIX" --disable-examples --disable-unit-tests
      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd ..
    }

    build_lame() {
      echo "📦 Сборка: libmp3lame"
      curl -LO https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz
      tar xzvf lame-3.100.tar.gz
      cd lame-3.100
      ./configure --prefix="$PREFIX" --enable-nasm --disable-shared
      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd ..
    }

    build_fdk_aac() {
      echo "📦 Сборка: fdk-aac"
      git clone --depth 1 https://github.com/mstorsjo/fdk-aac
      cd fdk-aac
      autoreconf -fiv
      ./configure --prefix="$PREFIX" --disable-shared
      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd ..
    }

    build_opus() {
      echo "📦 Сборка: libopus"
      curl -LO https://downloads.xiph.org/releases/opus/opus-1.3.1.tar.gz
      tar xzvf opus-1.3.1.tar.gz
      cd opus-1.3.1
      ./configure --prefix="$PREFIX" --disable-shared
      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd ..
    }

    build_ffmpeg() {
      echo "🎬 Сборка: ffmpeg"
      git clone https://github.com/FFmpeg/FFmpeg ffmpeg
      cd ffmpeg
      ./configure --prefix="$PREFIX" \
        --pkg-config-flags="--static" \
        --extra-cflags="-I$PREFIX/include" \
        --extra-ldflags="-L$PREFIX/lib" \
        --extra-libs="-lpthread -lm" \
        --enable-gpl --enable-nonfree \
        --enable-libx264 --enable-libx265 \
        --enable-libvpx --enable-libmp3lame \
        --enable-libfdk_aac --enable-libopus \
        --disable-shared --enable-static

      make -j$(nproc || sysctl -n hw.logicalcpu)
      make install
      cd ..
    }

    # Выполнение всех шагов сборки
    build_nasm
    build_yasm
    build_x264
    build_x265
    build_libvpx
    build_lame
    build_fdk_aac
    build_opus
    build_ffmpeg

    echo "✅ ffmpeg успешно собран и установлен в: $PREFIX"
  fi
fi

# ---------------------------------------------------------
# Конвертация mp3 → wav + удаление + подсчёт
# ---------------------------------------------------------
echo "🔄 Начинаем конвертацию mp3 → wav"
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
