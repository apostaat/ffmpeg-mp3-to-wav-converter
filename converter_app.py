#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
import json
import re
from pathlib import Path

def check_and_install_dependencies():
    """Check and install required dependencies."""
    # Skip dependency installation if running as a bundled application
    if getattr(sys, 'frozen', False):
        return
        
    try:
        import PyQt6
    except ImportError:
        print("Installing PyQt6...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
    
    # Check if ffmpeg is installed
    if not shutil.which('ffmpeg'):
        print("Installing ffmpeg...")
        if sys.platform == 'darwin':  # macOS
            subprocess.check_call(['brew', 'install', 'ffmpeg'])
        elif sys.platform == 'linux':  # Linux
            subprocess.check_call(['apt-get', 'update'])
            subprocess.check_call(['apt-get', 'install', '-y', 'ffmpeg'])
        elif sys.platform == 'win32':  # Windows
            print("Please install ffmpeg manually from https://ffmpeg.org/download.html")
            sys.exit(1)

# Check and install dependencies before importing PyQt6
check_and_install_dependencies()

from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QFileDialog, QLabel, QProgressBar, QTextEdit,
                            QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

def get_ffmpeg_path():
    """Get the path to FFmpeg executable."""
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        return os.path.join(sys._MEIPASS, 'ffmpeg')
    else:
        # Running in normal Python environment
        # Try to find FFmpeg in system PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path
        # Fallback to common installation paths
        common_paths = [
            '/usr/local/bin/ffmpeg',
            '/usr/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',
            '/opt/local/bin/ffmpeg'
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        return 'ffmpeg'  # Last resort, let the system PATH handle it

def get_ffprobe_path(ffmpeg_path=None):
    """Get the path to FFprobe executable (if available)."""
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'ffprobe')
        if os.path.exists(bundled):
            return bundled
    ffprobe_path = shutil.which('ffprobe')
    if ffprobe_path:
        return ffprobe_path
    if ffmpeg_path:
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        for name in ("ffprobe", "ffprobe.exe"):
            candidate = os.path.join(ffmpeg_dir, name)
            if os.path.exists(candidate):
                return candidate
    common_paths = [
        '/usr/local/bin/ffprobe',
        '/usr/bin/ffprobe',
        '/opt/homebrew/bin/ffprobe',
        '/opt/local/bin/ffprobe'
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

MAX_SAMPLE_RATE = 48000
LOSSY_CODECS = {
    "mp3", "mp2",
    "aac",
    "opus", "vorbis",
    "wma", "wmav1", "wmav2",
    "ac3", "eac3"
}
LOSSY_EXTENSIONS = {"mp3", "mp2", "aac", "m4a", "ogg", "opus", "wma"}
FILTER_CHAIN_PRIMARY = "adeclick,adeclip,anequalizer=c0 f=10000 w=1000 g=-5 t=1"
FILTER_CHAIN_FALLBACK = "anequalizer=c0 f=10000 w=1000 g=-5 t=1"

class ConversionWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int)  # success_count, error_count
    error = pyqtSignal(str)  # New signal for critical errors

    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.ffmpeg_path = get_ffmpeg_path()
        self.ffprobe_path = get_ffprobe_path(self.ffmpeg_path)

    def transliterate(self, text):
        # Транслитерация кириллицы в латиницу
        text = text.translate(str.maketrans(
            'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
            'abvgdeejzijklmnoprstufhzcss_y_euaABVGDEEJZIJKLMNOPRSTUFHZCSS_Y_EUA'
        ))
        return text

    def sanitize_filename(self, filename):
        # Транслитерация кириллицы
        filename = self.transliterate(filename)
        
        # Удаляем все специальные символы, оставляем только буквы и цифры
        filename = ''.join(c for c in filename if c.isalnum())
        
        # Если имя файла пустое после всех преобразований, используем "untitled"
        if not filename:
            filename = "untitled"
        
        # Приводим к нижнему регистру
        filename = filename.lower()
        
        return filename

    def _parse_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _sample_fmt_to_bit_depth(self, sample_fmt):
        if not sample_fmt:
            return None
        if sample_fmt.startswith(("s", "u")):
            match = re.match(r'[su](\d+)', sample_fmt)
            if match:
                return self._parse_int(match.group(1))
        if sample_fmt.startswith("flt"):
            return 32
        if sample_fmt.startswith("dbl"):
            return 64
        return None

    def _probe_audio_with_ffprobe(self, audiofile):
        if not self.ffprobe_path or not os.path.exists(self.ffprobe_path):
            return None
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=sample_rate,sample_fmt,bits_per_raw_sample,bit_depth,codec_name",
                    "-of", "json",
                    audiofile
                ],
                capture_output=True,
                text=True
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            data = json.loads(result.stdout)
            streams = data.get("streams") or []
            if not streams:
                return None
            stream = streams[0]
            bit_depth = self._parse_int(stream.get("bits_per_raw_sample"))
            if bit_depth is None:
                bit_depth = self._parse_int(stream.get("bit_depth"))
            sample_fmt = stream.get("sample_fmt")
            if bit_depth is None:
                bit_depth = self._sample_fmt_to_bit_depth(sample_fmt)
            return {
                "sample_rate": self._parse_int(stream.get("sample_rate")),
                "sample_fmt": sample_fmt,
                "bit_depth": bit_depth,
                "codec_name": stream.get("codec_name")
            }
        except Exception:
            return None

    def _probe_audio_with_ffmpeg(self, audiofile):
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-i", audiofile],
                capture_output=True,
                text=True
            )
            text = result.stderr or result.stdout or ""
            audio_line = None
            for line in text.splitlines():
                if "Audio:" in line:
                    audio_line = line
                    break
            if not audio_line:
                return None
            sample_rate = None
            match = re.search(r'(\d+)\s*Hz', audio_line)
            if match:
                sample_rate = self._parse_int(match.group(1))
            sample_fmt = None
            match = re.search(r'\b(s\d{1,2}p?|u\d{1,2}|flt|fltp|dbl|dblp)\b', audio_line)
            if match:
                sample_fmt = match.group(1)
            bit_depth = self._sample_fmt_to_bit_depth(sample_fmt)
            return {
                "sample_rate": sample_rate,
                "sample_fmt": sample_fmt,
                "bit_depth": bit_depth,
                "codec_name": None
            }
        except Exception:
            return None

    def _get_audio_info(self, audiofile):
        info = self._probe_audio_with_ffprobe(audiofile)
        if info:
            return info
        info = self._probe_audio_with_ffmpeg(audiofile)
        if info:
            return info
        return {"sample_rate": None, "sample_fmt": None, "bit_depth": None, "codec_name": None}

    def _needs_16bit(self, bit_depth, sample_fmt):
        if bit_depth is not None:
            return bit_depth > 16
        inferred = self._sample_fmt_to_bit_depth(sample_fmt)
        if inferred is not None:
            return inferred > 16
        return True

    def _needs_resample(self, sample_rate):
        return sample_rate is not None and sample_rate > MAX_SAMPLE_RATE

    def _should_apply_filters(self, audiofile, audio_info):
        codec = (audio_info.get("codec_name") or "").lower()
        if codec in LOSSY_CODECS:
            return True
        ext = Path(audiofile).suffix.lower().lstrip(".")
        if ext in LOSSY_EXTENSIONS:
            return True
        return codec == ""

    def _is_filter_error(self, stderr_text):
        if not stderr_text:
            return False
        text = stderr_text.lower()
        return "no such filter" in text or "error initializing filter" in text

    def _run_ffmpeg_with_fallbacks(self, cmd, fallback_cmds):
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result
        if self._is_filter_error(result.stderr):
            for fallback in fallback_cmds:
                result = subprocess.run(
                    fallback,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result
        return result

    def run(self):
        try:
            if not os.path.exists(self.directory):
                self.error.emit("Выбранная директория не существует")
                return

            if not os.access(self.directory, os.W_OK):
                self.error.emit("Нет прав на запись в выбранную директорию")
                return

            # Проверяем доступность FFmpeg
            if not os.path.exists(self.ffmpeg_path):
                self.error.emit(f"FFmpeg не найден по пути: {self.ffmpeg_path}")
                return

            # Делаем FFmpeg исполняемым
            if os.path.exists(self.ffmpeg_path):
                os.chmod(self.ffmpeg_path, 0o755)
            if self.ffprobe_path and os.path.exists(self.ffprobe_path):
                os.chmod(self.ffprobe_path, 0o755)

            success_count = 0
            error_count = 0
            
            # Поддерживаемые форматы
            audio_extensions = ["mp3", "wav", "aac", "m4a", "flac", "ogg", "wma", "aiff", "alac", "tak"]
            
            for ext in audio_extensions:
                for root, _, files in os.walk(self.directory):
                    for file in files:
                        if file.lower().endswith(f'.{ext}'):
                            audiofile = os.path.join(root, file)
                            
                            # Создаем новое имя файла
                            filename = os.path.splitext(file)[0]
                            new_filename = self.sanitize_filename(filename)
                            wavfile = os.path.join(root, f"{new_filename}.wav")
                            
                            # Если файл с таким именем уже существует, добавляем числовой суффикс
                            counter = 1
                            while os.path.exists(wavfile):
                                if new_filename == "untitled":
                                    wavfile = os.path.join(root, f"untitled{counter}.wav")
                                else:
                                    wavfile = os.path.join(root, f"{new_filename}_{counter}.wav")
                                counter += 1
                            
                            self.progress.emit(f"🔄 Конвертация: {audiofile}")
                            self.progress.emit(f"📝 Новое имя: {wavfile}")
                            
                            try:
                                audio_info = self._get_audio_info(audiofile)
                                sample_rate = audio_info.get("sample_rate")
                                bit_depth = audio_info.get("bit_depth")
                                sample_fmt = audio_info.get("sample_fmt")

                                needs_16bit = self._needs_16bit(bit_depth, sample_fmt)
                                needs_resample = self._needs_resample(sample_rate)

                                ffmpeg_cmd = [self.ffmpeg_path, "-loglevel", "warning", "-y", "-i", audiofile]
                                if needs_16bit:
                                    ffmpeg_cmd += ["-c:a", "pcm_s16le"]
                                if needs_resample:
                                    ffmpeg_cmd += ["-ar", str(MAX_SAMPLE_RATE)]
                                apply_filters = self._should_apply_filters(audiofile, audio_info)

                                # Конвертируем файл
                                if apply_filters:
                                    primary = ffmpeg_cmd + ["-af", FILTER_CHAIN_PRIMARY, wavfile]
                                    fallback = ffmpeg_cmd + ["-af", FILTER_CHAIN_FALLBACK, wavfile]
                                    no_filters = ffmpeg_cmd + [wavfile]
                                    result = self._run_ffmpeg_with_fallbacks(primary, [fallback, no_filters])
                                else:
                                    result = subprocess.run(
                                        ffmpeg_cmd + [wavfile],
                                        capture_output=True,
                                        text=True
                                    )
                                
                                if result.returncode == 0 and os.path.getsize(wavfile) > 0:
                                    self.progress.emit(f"✅ Успешно: {audiofile} → {wavfile}")
                                    os.remove(audiofile)
                                    success_count += 1
                                else:
                                    self.progress.emit(f"❌ Ошибка при конвертации: {audiofile}")
                                    if os.path.exists(wavfile):
                                        os.remove(wavfile)
                                    error_count += 1
                            except Exception as e:
                                self.progress.emit(f"❌ Ошибка: {str(e)}")
                                error_count += 1
            
            self.finished.emit(success_count, error_count)
        except Exception as e:
            self.error.emit(f"Критическая ошибка: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Converter")
        self.setMinimumSize(600, 400)
        
        # Создаем центральный виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Кнопка выбора директории
        self.select_button = QPushButton("Выбрать папку")
        self.select_button.clicked.connect(self.select_directory)
        layout.addWidget(self.select_button)
        
        # Метка с выбранной директорией
        self.directory_label = QLabel("Папка не выбрана")
        layout.addWidget(self.directory_label)
        
        # Кнопка конвертации
        self.convert_button = QPushButton("Конвертировать")
        self.convert_button.clicked.connect(self.start_conversion)
        self.convert_button.setEnabled(False)
        layout.addWidget(self.convert_button)
        
        # Прогресс
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        layout.addWidget(self.progress_text)
        
        self.selected_directory = None
        self.worker = None

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку с аудио файлами")
        if directory:
            if not os.access(directory, os.W_OK):
                QMessageBox.warning(self, "Ошибка", "Нет прав на запись в выбранную директорию")
                return
            self.selected_directory = directory
            self.directory_label.setText(f"Выбрана папка: {directory}")
            self.convert_button.setEnabled(True)

    def start_conversion(self):
        if not self.selected_directory:
            return
        
        self.convert_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.progress_text.clear()
        
        self.worker = ConversionWorker(self.selected_directory)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def update_progress(self, message):
        self.progress_text.append(message)
        # Прокручиваем к последней строке
        self.progress_text.verticalScrollBar().setValue(
            self.progress_text.verticalScrollBar().maximum()
        )

    def handle_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)
        self.convert_button.setEnabled(True)
        self.select_button.setEnabled(True)

    def conversion_finished(self, success_count, error_count):
        self.convert_button.setEnabled(True)
        self.select_button.setEnabled(True)
        
        self.progress_text.append(f"\n🎉 Готово! Конвертировано файлов: {success_count}")
        if error_count > 0:
            self.progress_text.append(f"⚠️  Количество ошибок: {error_count}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 
