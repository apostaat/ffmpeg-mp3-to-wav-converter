#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
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

class ConversionWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int)  # success_count, error_count
    error = pyqtSignal(str)  # New signal for critical errors

    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.ffmpeg_path = get_ffmpeg_path()

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

            success_count = 0
            error_count = 0
            
            # Поддерживаемые форматы
            audio_extensions = ["mp3", "wav", "aac", "m4a", "flac", "ogg", "wma", "aiff", "alac"]
            
            for ext in audio_extensions:
                for root, _, files in os.walk(self.directory):
                    for file in files:
                        if file.lower().endswith(f'.{ext}'):
                            audiofile = os.path.join(root, file)
                            
                            # Пропускаем файлы, которые уже являются WAV
                            if ext == "wav":
                                continue
                            
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
                                # Конвертируем файл
                                result = subprocess.run(
                                    [self.ffmpeg_path, "-loglevel", "warning", "-y", "-i", audiofile, "-ar", "44100", wavfile],
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