.PHONY: check-python check-pip venv check-ffmpeg install-deps app clean up

# Проверка и установка Python
check-python:
	@echo "🔍 Проверка Python..."
	@if ! command -v python3 &> /dev/null; then \
		if [ "$(shell uname)" = "Darwin" ]; then \
			if ! command -v brew &> /dev/null; then \
				echo "❌ Homebrew не установлен. Пожалуйста, установите Homebrew:"; \
				echo "   /bin/bash -c \"\$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""; \
				exit 1; \
			fi; \
			echo "📦 Установка Python через Homebrew..."; \
			brew install python; \
		elif [ "$(shell uname)" = "Linux" ]; then \
			echo "📦 Установка Python через apt..."; \
			sudo apt-get update && sudo apt-get install -y python3 python3-pip; \
		else \
			echo "❌ Не удалось установить Python автоматически. Пожалуйста, установите Python 3 вручную."; \
			exit 1; \
		fi \
	fi

# Проверка и установка pip
check-pip: check-python
	@echo "🔍 Проверка pip..."
	@if ! command -v pip3 &> /dev/null; then \
		if [ "$(shell uname)" = "Darwin" ]; then \
			if ! command -v brew &> /dev/null; then \
				echo "❌ Homebrew не установлен. Пожалуйста, установите Homebrew:"; \
				echo "   /bin/bash -c \"\$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""; \
				exit 1; \
			fi; \
			echo "📦 Установка pip через Homebrew..."; \
			brew install python; \
		elif [ "$(shell uname)" = "Linux" ]; then \
			echo "📦 Установка pip через apt..."; \
			sudo apt-get update && sudo apt-get install -y python3-pip; \
		else \
			echo "❌ Не удалось установить pip автоматически. Пожалуйста, установите pip вручную."; \
			exit 1; \
		fi \
	fi

# Проверка и установка FFmpeg
check-ffmpeg:
	@echo "🔍 Проверка FFmpeg..."
	@if ! command -v ffmpeg &> /dev/null; then \
		if [ "$(shell uname)" = "Darwin" ]; then \
			if ! command -v brew &> /dev/null; then \
				echo "❌ Homebrew не установлен. Пожалуйста, установите Homebrew:"; \
				echo "   /bin/bash -c \"\$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""; \
				exit 1; \
			fi; \
			echo "📦 Установка FFmpeg через Homebrew..."; \
			brew install ffmpeg; \
		elif [ "$(shell uname)" = "Linux" ]; then \
			echo "📦 Установка FFmpeg через apt..."; \
			sudo apt-get update && sudo apt-get install -y ffmpeg; \
		else \
			echo "❌ Не удалось установить FFmpeg автоматически. Пожалуйста, установите FFmpeg вручную."; \
			exit 1; \
		fi \
	fi

# Создание виртуального окружения
venv: check-pip
	@echo "🔧 Создание виртуального окружения..."
	@if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate || . venv/Scripts/activate

# Установка зависимостей
install-deps: venv check-ffmpeg
	@echo "📦 Установка зависимостей..."
	@. venv/bin/activate || . venv/Scripts/activate; \
	pip install --upgrade pip; \
	pip install -r requirements.txt; \
	if [ "$(shell uname)" = "Darwin" ]; then \
		pip install --upgrade PyQt6; \
	fi

# Запуск приложения
app: install-deps
	@echo "🚀 Запуск приложения..."
	@. venv/bin/activate || . venv/Scripts/activate; \
	python3 build.py

# Очистка
clean:
	@echo "🧹 Очистка..."
	@rm -rf __pycache__ *.pyc
	@rm -rf venv
	@rm -rf dist
	@rm -rf build
	@rm -rf *.spec
	@rm -rf ffmpeg_bin
	@rm -rf icon.iconset
	@rm -f *.icns
	@rm -f *.zip

# Помощь
help:
	@echo "Доступные команды:"
	@echo "  make app     - Установить зависимости и запустить приложение"
	@echo "  make clean   - Очистить временные файлы"
	@echo "  make help    - Показать это сообщение"

# Запуск приложения с использованием Docker
up:
	docker-compose up --build 