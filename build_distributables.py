#!/usr/bin/env python3
"""
Build script for creating macOS .app and Windows .exe distributables
for the MP3 to WAV Converter application.
"""

import os
import sys
import platform
import subprocess
import shutil
import urllib.request
import zipfile
import tempfile
from pathlib import Path
import json

class BuildConfig:
    """Configuration for the build process."""
    
    def __init__(self):
        self.app_name = "Audio Converter"
        self.app_version = "1.0.0"
        self.bundle_id = "com.audioconverter.app"
        self.dist_dir = "dist"
        self.build_dir = "build"
        self.ffmpeg_dir = "ffmpeg_bin"
        self.icon_png = "logo.png"
        self.icon_icns = "logo.icns"
        self.icon_ico = "logo.ico"
        
        # Platform-specific FFmpeg URLs
        self.ffmpeg_urls = {
            'darwin': 'https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip',
            'win32': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'
        }
        
        # Platform-specific icon sizes
        self.icon_sizes = {
            'darwin': [16, 32, 64, 128, 256, 512, 1024],
            'win32': [16, 24, 32, 48, 64, 128, 256]
        }

class BuildManager:
    """Manages the build process for different platforms."""
    
    def __init__(self):
        self.config = BuildConfig()
        self.platform = platform.system().lower()
        self.is_macos = self.platform == 'darwin'
        self.is_windows = self.platform == 'windows'
        self.is_linux = self.platform == 'linux'
        
    def log(self, message, level="INFO"):
        """Log messages with timestamps."""
        print(f"[{level}] {message}")
        
    def check_dependencies(self):
        """Check if required dependencies are installed."""
        self.log("Checking dependencies...")
        
        # Check Python
        if sys.version_info < (3, 8):
            self.log("Python 3.8+ is required", "ERROR")
            return False
            
        # Check pip
        try:
            import pip
        except ImportError:
            self.log("pip is not installed", "ERROR")
            return False
            
        return True
        
    def install_build_dependencies(self):
        """Install required build dependencies."""
        self.log("Installing build dependencies...")
        
        dependencies = [
            "pyinstaller>=5.0",
            "pillow>=9.0",
            "requests>=2.25"
        ]
        
        for dep in dependencies:
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", dep
                ])
                self.log(f"Installed {dep}")
            except subprocess.CalledProcessError as e:
                self.log(f"Failed to install {dep}: {e}", "ERROR")
                return False
                
        return True
        
    def download_ffmpeg(self):
        """Download FFmpeg binary for the current platform."""
        self.log("Downloading FFmpeg...")
        
        if self.platform not in self.config.ffmpeg_urls:
            self.log(f"FFmpeg download not supported for {self.platform}", "ERROR")
            return False
            
        url = self.config.ffmpeg_urls[self.platform]
        ffmpeg_zip = f"ffmpeg_{self.platform}.zip"
        
        try:
            # Create ffmpeg directory
            os.makedirs(self.config.ffmpeg_dir, exist_ok=True)
            
            # Download FFmpeg
            self.log(f"Downloading from {url}")
            urllib.request.urlretrieve(url, ffmpeg_zip)
            
            # Extract FFmpeg
            with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                zip_ref.extractall(self.config.ffmpeg_dir)
                
            # Find and move ffmpeg binary
            ffmpeg_binary = self._find_ffmpeg_binary()
            if ffmpeg_binary:
                target_path = os.path.join(self.config.ffmpeg_dir, "ffmpeg")
                if self.is_windows:
                    target_path += ".exe"
                    
                shutil.move(ffmpeg_binary, target_path)
                os.chmod(target_path, 0o755)
                self.log(f"FFmpeg installed to {target_path}")
                
            # Clean up
            os.remove(ffmpeg_zip)
            self._cleanup_ffmpeg_extract()
            
            return True
            
        except Exception as e:
            self.log(f"Failed to download FFmpeg: {e}", "ERROR")
            return False
            
    def _find_ffmpeg_binary(self):
        """Find the FFmpeg binary in the extracted files."""
        for root, dirs, files in os.walk(self.config.ffmpeg_dir):
            for file in files:
                if file == "ffmpeg" or file == "ffmpeg.exe":
                    return os.path.join(root, file)
        return None
        
    def _cleanup_ffmpeg_extract(self):
        """Clean up unnecessary files from FFmpeg extraction."""
        # Remove empty directories and unnecessary files
        for root, dirs, files in os.walk(self.config.ffmpeg_dir, topdown=False):
            for file in files:
                if file.endswith(('.txt', '.md', '.html')):
                    os.remove(os.path.join(root, file))
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except OSError:
                    pass
                    
    def create_icons(self):
        """Create platform-specific icons."""
        self.log("Creating icons...")
        
        if not os.path.exists(self.config.icon_png):
            self.log(f"Icon file {self.config.icon_png} not found", "ERROR")
            return False
            
        try:
            from PIL import Image
            
            if self.is_macos:
                return self._create_icns_icon()
            elif self.is_windows:
                return self._create_ico_icon()
            else:
                self.log("Icon creation not supported for this platform", "WARNING")
                return True
                
        except ImportError:
            self.log("PIL/Pillow not available for icon creation", "WARNING")
            return True
            
    def _create_icns_icon(self):
        """Create ICNS icon for macOS."""
        try:
            from PIL import Image
            
            # Create iconset directory
            iconset_dir = "icon.iconset"
            os.makedirs(iconset_dir, exist_ok=True)
            
            # Load source image
            img = Image.open(self.config.icon_png)
            
            # Create icons of different sizes
            sizes = self.config.icon_sizes['darwin']
            for size in sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(f"{iconset_dir}/icon_{size}x{size}.png")
                
                # Create @2x versions for retina displays
                if size <= 512:
                    resized.save(f"{iconset_dir}/icon_{size//2}x{size//2}@2x.png")
                    
            # Convert to ICNS
            subprocess.check_call(['iconutil', '-c', 'icns', iconset_dir])
            shutil.move('icon.icns', self.config.icon_icns)
            
            # Clean up
            shutil.rmtree(iconset_dir)
            
            self.log(f"Created {self.config.icon_icns}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create ICNS icon: {e}", "ERROR")
            return False
            
    def _create_ico_icon(self):
        """Create ICO icon for Windows."""
        try:
            from PIL import Image
            
            # Load source image
            img = Image.open(self.config.icon_png)
            
            # Create ICO with multiple sizes
            sizes = self.config.icon_sizes['win32']
            icons = []
            for size in sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                icons.append(resized)
                
            # Save as ICO
            icons[0].save(self.config.icon_ico, format='ICO', sizes=[(s, s) for s in sizes])
            
            self.log(f"Created {self.config.icon_ico}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create ICO icon: {e}", "ERROR")
            return False
            
    def create_spec_file(self):
        """Create PyInstaller spec file."""
        self.log("Creating PyInstaller spec file...")
        
        # Determine FFmpeg binary path
        ffmpeg_binary = os.path.join(self.config.ffmpeg_dir, "ffmpeg")
        if self.is_windows:
            ffmpeg_binary += ".exe"
            
        # Determine icon file
        icon_file = None
        if self.is_macos and os.path.exists(self.config.icon_icns):
            icon_file = self.config.icon_icns
        elif self.is_windows and os.path.exists(self.config.icon_ico):
            icon_file = self.config.icon_ico
            
        # Create spec file content
        icon_line = f"icon='{icon_file}'" if icon_file else "icon=None"
        cwd_repr = repr(os.getcwd())

        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')

a = Analysis(
    ['converter_app.py'],
    pathex=[{cwd_repr}],
    binaries=[('{ffmpeg_binary}', '.')] + pyqt6_binaries,
    datas=pyqt6_datas,
    hiddenimports=['pkgutil'] + pyqt6_hiddenimports,
    hookspath=[],
    hooksconfig={{}},
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
    [],
    exclude_binaries=True,
    name='{self.config.app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_line}
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.config.app_name}'
)'''

        if self.is_macos:
            bundle_icon_line = f"icon='{icon_file}'" if icon_file else "icon=None"
            spec_content += f'''

app = BUNDLE(
    coll,
    name='{self.config.app_name}.app',
    {bundle_icon_line},
    bundle_identifier='{self.config.bundle_id}',
    info_plist={{
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': '{self.config.app_version}',
        'CFBundleVersion': '{self.config.app_version}',
        'CFBundleDisplayName': '{self.config.app_name}',
        'CFBundleName': '{self.config.app_name}',
        'CFBundleExecutable': '{self.config.app_name}',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSMinimumSystemVersion': '10.13',
    }},
)'''
        
        # Write spec file
        spec_file = f"{self.config.app_name}.spec"
        with open(spec_file, 'w') as f:
            f.write(spec_content)
            
        self.log(f"Created {spec_file}")
        return spec_file
        
    def build_application(self, spec_file):
        """Build the application using PyInstaller."""
        self.log("Building application...")
        
        try:
            # Clean previous builds
            if os.path.exists(self.config.dist_dir):
                shutil.rmtree(self.config.dist_dir)
            if os.path.exists(self.config.build_dir):
                shutil.rmtree(self.config.build_dir)
                
            # Run PyInstaller
            cmd = [sys.executable, "-m", "PyInstaller", "--clean", spec_file]
            subprocess.check_call(cmd)
            
            self.log("Build completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Build failed: {e}", "ERROR")
            return False
            
    def create_installer(self):
        """Create platform-specific installer."""
        self.log("Creating installer...")
        
        if self.is_macos:
            return self._create_dmg()
        elif self.is_windows:
            return self._create_installer_exe()
        else:
            self.log("Installer creation not supported for this platform", "WARNING")
            return True
            
    def _create_dmg(self):
        """Create DMG installer for macOS."""
        try:
            app_path = os.path.join(self.config.dist_dir, f"{self.config.app_name}.app")
            if not os.path.exists(app_path):
                self.log("App bundle not found", "ERROR")
                return False
                
            dmg_name = f"{self.config.app_name}.dmg"
            dmg_path = os.path.join(self.config.dist_dir, dmg_name)
            
            # Create temporary directory for DMG content
            dmg_content = os.path.join(self.config.dist_dir, "dmg_content")
            os.makedirs(dmg_content, exist_ok=True)
            
            # Copy app to DMG content
            shutil.copytree(app_path, os.path.join(dmg_content, f"{self.config.app_name}.app"))
            
            # Create DMG
            if shutil.which('create-dmg'):
                cmd = [
                    'create-dmg',
                    '--volname', self.config.app_name,
                    '--window-pos', '200', '120',
                    '--window-size', '800', '400',
                    '--icon-size', '100',
                    '--app-drop-link', '600', '200',
                    dmg_path,
                    dmg_content
                ]
                subprocess.check_call(cmd)
            else:
                # Fallback to hdiutil
                cmd = [
                    'hdiutil', 'create',
                    '-volname', self.config.app_name,
                    '-srcfolder', dmg_content,
                    '-ov',
                    '-format', 'UDZO',
                    dmg_path
                ]
                subprocess.check_call(cmd)
                
            # Clean up
            shutil.rmtree(dmg_content)
            
            self.log(f"Created DMG: {dmg_path}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create DMG: {e}", "ERROR")
            return False
            
    def _create_installer_exe(self):
        """Create Windows installer (placeholder)."""
        # For Windows, we could use NSIS or Inno Setup
        # For now, just create a simple ZIP archive
        try:
            app_path = os.path.join(self.config.dist_dir, f"{self.config.app_name}.exe")
            if not os.path.exists(app_path):
                self.log("Executable not found", "ERROR")
                return False
                
            zip_name = f"{self.config.app_name}_Windows.zip"
            zip_path = os.path.join(self.config.dist_dir, zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(app_path, f"{self.config.app_name}.exe")
                
            self.log(f"Created ZIP: {zip_path}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create ZIP: {e}", "ERROR")
            return False
            
    def cleanup(self):
        """Clean up temporary files."""
        self.log("Cleaning up...")
        
        cleanup_paths = [
            self.config.build_dir,
            self.config.ffmpeg_dir,
            f"{self.config.app_name}.spec",
            "icon.iconset",
            "icon.icns",
            "icon.ico"
        ]
        
        for path in cleanup_paths:
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                    
    def build(self):
        """Main build process."""
        self.log(f"Starting build for {self.platform}")
        
        try:
            # Check dependencies
            if not self.check_dependencies():
                return False
                
            # Install build dependencies
            if not self.install_build_dependencies():
                return False
                
            # Download FFmpeg
            if not self.download_ffmpeg():
                return False
                
            # Create icons
            if not self.create_icons():
                return False
                
            # Create spec file
            spec_file = self.create_spec_file()
            if not spec_file:
                return False
                
            # Build application
            if not self.build_application(spec_file):
                return False
                
            # Create installer
            if not self.create_installer():
                return False
                
            self.log("Build completed successfully!")
            self.log(f"Output directory: {self.config.dist_dir}")
            
            return True
            
        except Exception as e:
            self.log(f"Build failed: {e}", "ERROR")
            return False
        finally:
            # Clean up temporary files
            self.cleanup()

def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Build script for MP3 to WAV Converter

Usage: python build_distributables.py [options]

Options:
  --help          Show this help message
  --clean         Clean build artifacts only
  --no-cleanup    Don't clean up temporary files

Examples:
  python build_distributables.py              # Build for current platform
  python build_distributables.py --clean      # Clean build artifacts
        """)
        return
        
    # Parse arguments
    clean_only = "--clean" in sys.argv
    no_cleanup = "--no-cleanup" in sys.argv
    
    builder = BuildManager()
    
    if clean_only:
        builder.cleanup()
        print("Build artifacts cleaned.")
        return
        
    # Build the application
    success = builder.build()
    
    if not no_cleanup and success:
        builder.cleanup()
        
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
