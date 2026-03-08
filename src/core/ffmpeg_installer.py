"""
Модуль для автоматической установки FFmpeg.
"""

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
    FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    # Установка в папку пользователя (не требует прав администратора)
    INSTALL_DIR = Path.home() / "FFmpegGUI" / "ffmpeg"
    
    _cancel_flag = False
    
    @classmethod
    def is_installed(cls) -> bool:
        """Проверка установлен ли FFmpeg."""
        return cls.get_ffmpeg_path() is not None
    
    @classmethod
    def get_ffmpeg_path(cls) -> str | None:
        """Получить путь к FFmpeg."""
        # Проверяем в PATH
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            return ffmpeg_in_path
        
        # Проверяем в директории установки
        ffmpeg_exe = cls.INSTALL_DIR / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)
        
        return None
    
    @classmethod
    def cancel_installation(cls):
        """Отменить установку."""
        cls._cancel_flag = True
    
    @classmethod
    def reset_cancel_flag(cls):
        """Сбросить флаг отмены."""
        cls._cancel_flag = False
    
    @classmethod
    def download_ffmpeg(cls, progress_callback=None) -> Path:
        """Скачать FFmpeg."""
        temp_dir = Path(tempfile.gettempdir()) / "ffmpeggui_install"
        temp_dir.mkdir(exist_ok=True)
        
        zip_path = temp_dir / "ffmpeg.zip"
        
        print(f"Downloading from: {cls.FFMPEG_URL}")
        print(f"To: {zip_path}")
        
        def report_progress(block_num, block_size, total_size):
            if cls._cancel_flag:
                raise Exception("Установка отменена пользователем")
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            if progress_callback:
                progress_callback(percent)
        
        # Пробуем несколько методов загрузки
        try:
            print("Method 1: urllib.request")
            urllib.request.urlretrieve(cls.FFMPEG_URL, zip_path, report_progress)
        except Exception as e1:
            print(f"urllib failed: {e1}")
            try:
                print("Method 2: requests")
                import requests
                response = requests.get(cls.FFMPEG_URL, stream=True)
                total = int(response.headers.get('content-length', 0))
                with open(zip_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if cls._cancel_flag:
                            raise Exception("Установка отменена")
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback((downloaded / total) * 100)
            except Exception as e2:
                print(f"requests failed: {e2}")
                raise Exception(f"Не удалось загрузить FFmpeg: {e1}")
        
        if not zip_path.exists() or zip_path.stat().st_size == 0:
            raise Exception("Файл не загрузился или пустой")
        
        print(f"Download complete: {zip_path.exists()}, size: {zip_path.stat().st_size}")
        return zip_path
    
    @classmethod
    def extract_ffmpeg(cls, zip_path: Path, dest_dir: Path, progress_callback=None):
        """Распаковать FFmpeg."""
        print(f"Extracting to: {dest_dir}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Находим папку с бинарниками
                members = zip_ref.namelist()
                print(f"Archive contains {len(members)} files")
                
                base_folder = None
                for member in members:
                    if 'bin/ffmpeg.exe' in member or 'bin\\ffmpeg.exe' in member:
                        base_folder = member.split('/')[0].replace('\\', '/')
                        break
                
                if not base_folder:
                    raise Exception("Не удалось найти бинарники FFmpeg в архиве")
                
                print(f"Base folder: {base_folder}")
                
                # Распаковываем только bin папку
                bin_folder = f"{base_folder}/bin/"
                members_to_extract = [m for m in members if m.startswith(bin_folder)]
                
                print(f"Extracting {len(members_to_extract)} files from {bin_folder}")
                
                total = len(members_to_extract)
                for i, member in enumerate(members_to_extract):
                    if cls._cancel_flag:
                        raise Exception("Установка отменена пользователем")
                    
                    # Извлекаем файлы из bin/ прямо в dest_dir
                    relative_path = member.replace(bin_folder, '')
                    dest_path = dest_dir / relative_path
                    
                    print(f"  Extracting: {member} -> {dest_path}")
                    
                    # Извлекаем
                    with zip_ref.open(member) as source:
                        with open(dest_path, 'wb') as target:
                            target.write(source.read())
                    
                    if progress_callback:
                        progress_callback((i / total) * 100)
                
                print(f"Extraction complete")
                
        except Exception as e:
            print(f"Extraction error: {e}")
            raise
    
    @classmethod
    def install(cls, progress_callback=None) -> bool:
        """
        Установить FFmpeg.
        Возвращает True если установка успешна.
        """
        cls.reset_cancel_flag()
        print("=" * 50)
        print("Starting FFmpeg installation")
        print("=" * 50)
        
        try:
            # Создаём директорию установки
            print(f"Creating directory: {cls.INSTALL_DIR}")
            cls.INSTALL_DIR.mkdir(exist_ok=True, parents=True)
            
            # Скачиваем
            if progress_callback:
                progress_callback("Скачивание FFmpeg...", 0)
            
            def download_progress(p):
                if progress_callback:
                    progress_callback("Скачивание...", p)
            
            zip_path = cls.download_ffmpeg(download_progress)
            
            if cls._cancel_flag:
                raise Exception("Установка отменена пользователем")
            
            # Распаковываем
            if progress_callback:
                progress_callback("Распаковка...", 0)
            
            def extract_progress(p):
                if progress_callback:
                    progress_callback("Распаковка...", p)
            
            cls.extract_ffmpeg(zip_path, cls.INSTALL_DIR, extract_progress)
            
            if cls._cancel_flag:
                raise Exception("Установка отменена пользователем")
            
            # Проверяем что файл существует
            ffmpeg_exe = cls.INSTALL_DIR / "ffmpeg.exe"
            if not ffmpeg_exe.exists():
                raise Exception(f"ffmpeg.exe не найден в {cls.INSTALL_DIR}")
            print(f"✓ FFmpeg installed: {ffmpeg_exe}")
            print(f"  Size: {ffmpeg_exe.stat().st_size} bytes")
            
            # Очищаем временные файлы
            zip_path.unlink()
            print(f"Cleaned up: {zip_path}")
            
            print("=" * 50)
            print("Installation complete!")
            print("=" * 50)
            return True
            
        except Exception as e:
            print(f"Installation error: {e}")
            import traceback
            traceback.print_exc()
            return False
