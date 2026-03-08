"""
Модуль для автоматической установки FFmpeg.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import urllib.request
import zipfile


class FFmpegInstaller:
    """Установщик FFmpeg для Windows."""
    
    # Официальный GitHub релиз от BtbN (зеркало ffmpeg.org)
    # https://github.com/BtbN/FFmpeg-Builds/releases
    FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    INSTALL_DIR = Path(r"C:\Program Files\FFmpegGUI")
    
    @classmethod
    def is_installed(cls) -> bool:
        """Проверка установлен ли FFmpeg."""
        # Проверяем в PATH
        if shutil.which("ffmpeg"):
            return True
        
        # Проверяем в директории установки
        ffmpeg_exe = cls.INSTALL_DIR / "bin" / "ffmpeg.exe"
        return ffmpeg_exe.exists()
    
    @classmethod
    def get_ffmpeg_path(cls) -> str | None:
        """Получить путь к FFmpeg."""
        # Проверяем в PATH
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            return ffmpeg_in_path
        
        # Проверяем в директории установки
        ffmpeg_exe = cls.INSTALL_DIR / "bin" / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)
        
        return None
    
    @classmethod
    def download_ffmpeg(cls, progress_callback=None) -> Path:
        """Скачать FFmpeg."""
        temp_dir = Path(tempfile.gettempdir()) / "ffmpeggui_install"
        temp_dir.mkdir(exist_ok=True)
        
        zip_path = temp_dir / "ffmpeg.zip"
        
        def report_progress(block_num, block_size, total_size):
            if progress_callback:
                downloaded = block_num * block_size
                percent = min(100, (downloaded / total_size) * 100)
                progress_callback(percent)
        
        urllib.request.urlretrieve(cls.FFMPEG_URL, zip_path, report_progress)
        return zip_path
    
    @classmethod
    def extract_ffmpeg(cls, zip_path: Path, dest_dir: Path, progress_callback=None):
        """Распаковать FFmpeg."""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Находим папку с бинарниками
            members = zip_ref.namelist()
            base_folder = None
            for member in members:
                if member.endswith('bin/ffmpeg.exe'):
                    base_folder = member.split('/')[0]
                    break
            
            if not base_folder:
                raise Exception("Не удалось найти бинарники FFmpeg в архиве")
            
            # Распаковываем только bin папку
            bin_folder = f"{base_folder}/bin/"
            members_to_extract = [m for m in members if m.startswith(bin_folder)]
            
            total = len(members_to_extract)
            for i, member in enumerate(members_to_extract):
                zip_ref.extract(member, dest_dir)
                if progress_callback:
                    progress_callback((i / total) * 100)
    
    @classmethod
    def add_to_path(cls) -> bool:
        """Добавить FFmpeg в системный PATH."""
        try:
            bin_path = str(cls.INSTALL_DIR / "bin")
            
            # Команда для добавления в системный PATH
            cmd = f'setx /M PATH "%PATH%;{bin_path}"'
            subprocess.run(cmd, shell=True, check=True)
            
            return True
        except Exception as e:
            print(f"Ошибка добавления в PATH: {e}")
            return False
    
    @classmethod
    def install(cls, progress_callback=None) -> bool:
        """
        Установить FFmpeg.
        Возвращает True если установка успешна.
        """
        try:
            # Создаём директорию установки
            cls.INSTALL_DIR.mkdir(exist_ok=True, parents=True)
            
            # Скачиваем
            if progress_callback:
                progress_callback("Скачивание FFmpeg...", 0)
            zip_path = cls.download_ffmpeg(lambda p: progress_callback("Скачивание...", p))
            
            # Распаковываем
            if progress_callback:
                progress_callback("Распаковка...", 0)
            cls.extract_ffmpeg(zip_path, cls.INSTALL_DIR, lambda p: progress_callback("Распаковка...", p))
            
            # Очищаем временные файлы
            zip_path.unlink()
            
            # Добавляем в PATH
            if progress_callback:
                progress_callback("Добавление в PATH...", 100)
            cls.add_to_path()
            
            return True
            
        except Exception as e:
            print(f"Ошибка установки: {e}")
            return False
