# Use Python 3.9 as base image
FROM python:3.9-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libegl1-mesa \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb1 \
    libxcb-util1 \
    libvips \
    libvips-dev \
    libgdk-pixbuf2.0-0 \
    libgdk-pixbuf2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY converter_app.py build.py .

# Set display for GUI
ENV DISPLAY=host.docker.internal:0

CMD ["python", "converter_app.py"] 