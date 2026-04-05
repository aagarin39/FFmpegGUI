"""
Модуль для автоматической установки FFmpeg (кроссплатформенный).

Поддерживает Windows, Linux, macOS.
"""

import sys
import tempfile
import shutil
import platform
from pathlib import Path
from typing import Optional, Callable, Any
import urllib.request
import zipfile


class FFmpegInstaller:
    """Кроссплатформенный установщик FFmpeg."""
    
    FFMPEG_URL = ""
    
    MIRROR_URLS = {
        "windows": [
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.0.1-win64-gpl.zip",
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        ],
    }
    
    _cancel_flag = False
    _platform: Optional[str] = None
    
    @classmethod
    def _get_platform(cls) -> str:
        """Определить текущую платформу."""
        if cls._platform is None:
            system = platform.system()
            if system == "Windows":
                cls._platform = "windows"
            elif system == "Linux":
                cls._platform = "linux"
            elif system == "Darwin":
                cls._platform = "macos"
            else:
                cls._platform = "unknown"
        return cls._platform
    
    @classmethod
    def _get_install_dir(cls) -> Path:
        """Получить директорию установки для текущей платформы."""
        plat = cls._get_platform()
        if plat == "windows":
            return Path.home() / "FFmpegGUI" / "ffmpeg"
        elif plat == "linux":
            return Path.home() / ".local" / "FFmpegGUI" / "bin"
        elif plat == "macos":
            return Path.home() / "Applications" / "FFmpegGUI"
        else:
            return Path.home() / "FFmpegGUI" / "ffmpeg"
    
    @classmethod
    def _get_ffmpeg_binary_name(cls) -> str:
        """Получить имя бинарного файла FFmpeg для платформы."""
        plat = cls._get_platform()
        if plat == "windows":
            return "ffmpeg.exe"
        else:
            return "ffmpeg"
    
    @classmethod
    def _get_ffprobe_binary_name(cls) -> str:
        """Получить имя бинарного файла ffprobe для платформы."""
        plat = cls._get_platform()
        if plat == "windows":
            return "ffprobe.exe"
        else:
            return "ffprobe"
    
    @classmethod
    def is_installed(cls) -> bool:
        """Проверка установлен ли FFmpeg."""
        return cls.get_ffmpeg_path() is not None
    
    @classmethod
    def get_ffmpeg_path(cls) -> Optional[str]:
        """Получить путь к FFmpeg."""
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            return ffmpeg_in_path
        
        install_dir = cls._get_install_dir()
        ffmpeg_binary = install_dir / cls._get_ffmpeg_binary_name()
        if ffmpeg_binary.exists():
            return str(ffmpeg_binary)
        
        return None
    
    @classmethod
    def get_ffmpeg_version(cls) -> str:
        """Получить версию из файла version.txt"""
        install_dir = cls._get_install_dir()
        version_file = install_dir / "version.txt"
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip()
        return "неизвестно"
    
    @classmethod
    def get_install_date(cls) -> str:
        """Получить дату установки из файла"""
        install_dir = cls._get_install_dir()
        date_file = install_dir / "install_date.txt"
        if date_file.exists():
            return date_file.read_text(encoding='utf-8').strip()
        return "неизвестно"
    
    @classmethod
    def validate_installation(cls) -> bool:
        """Проверить что все файлы на месте"""
        install_dir = cls._get_install_dir()
        ffmpeg_name = cls._get_ffmpeg_binary_name()
        ffprobe_name = cls._get_ffprobe_binary_name()
        plat = cls._get_platform()
        
        required = [ffmpeg_name, ffprobe_name]
        for file in required:
            if not (install_dir / file).exists():
                print(f"Missing required file: {file}")
                return False
        
        ffmpeg_path = install_dir / ffmpeg_name
        if ffmpeg_path.exists():
            ffmpeg_size = ffmpeg_path.stat().st_size
            if plat == "windows" and ffmpeg_size < 50 * 1024 * 1024:
                print(f"{ffmpeg_name} too small: {ffmpeg_size} bytes")
                return False
        
        return True
    
    @classmethod
    def rotate_logs(cls):
        """Сдвинуть логи: install.log -> .1 -> .2"""
        plat = cls._get_platform()
        if plat == "windows":
            log_base = Path.home() / "FFmpegGUI" / "install.log"
        elif plat == "linux":
            log_base = Path.home() / ".local" / "FFmpegGUI" / "install.log"
        elif plat == "macos":
            log_base = Path.home() / "Library" / "Application Support" / "FFmpegGUI" / "install.log"
        else:
            log_base = Path.home() / "FFmpegGUI" / "install.log"
        
        log_2 = log_base.with_suffix('.log.2')
        if log_2.exists():
            log_2.unlink()
        
        log_1 = log_base.with_suffix('.log.1')
        if log_1.exists():
            log_1.rename(log_2)
        
        if log_base.exists():
            log_base.rename(log_1)
    
    @classmethod
    def uninstall(cls) -> bool:
        """Удалить FFmpeg."""
        try:
            install_dir = cls._get_install_dir()
            if not install_dir.exists():
                return False
            
            print(f"Uninstalling FFmpeg from {install_dir}")
            shutil.rmtree(install_dir)
            return True
        except Exception as e:
            print(f"Uninstall error: {e}")
            return False
    
    @classmethod
    def cancel_installation(cls):
        """Отменить установку."""
        cls._cancel_flag = True
    
    @classmethod
    def reset_cancel_flag(cls):
        """Сбросить флаг отмены."""
        cls._cancel_flag = False
    
    @classmethod
    def _install_windows(cls, progress_callback: Optional[Callable] = None) -> bool:
        """Установить FFmpeg на Windows (скачивание и распаковка)."""
        cls.reset_cancel_flag()
        
        log_file = Path.home() / "FFmpegGUI" / "install.log"
        log_file.parent.mkdir(exist_ok=True)
        cls.rotate_logs()
        
        from io import StringIO
        log_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = log_buffer
        
        try:
            print("=" * 60)
            print("FFmpeg Installation Log (Windows)")
            print("=" * 60)
            print(f"Time: {__import__('datetime').datetime.now()}")
            
            install_dir = cls._get_install_dir()
            if install_dir.exists():
                print(f"Cleaning old installation: {install_dir}")
                shutil.rmtree(install_dir)
            
            install_dir.mkdir(exist_ok=True, parents=True)
            
            if progress_callback:
                progress_callback("Скачивание FFmpeg...", 0)
            
            def download_progress(p):
                if progress_callback:
                    progress_callback("Скачивание...", p)
            
            zip_path = cls._download_ffmpeg_windows(download_progress)
            
            if cls._cancel_flag:
                raise Exception("Установка отменена пользователем")
            
            if progress_callback:
                progress_callback("Распаковка...", 0)
            
            def extract_progress(p):
                if progress_callback:
                    progress_callback("Распаковка...", p)
            
            cls.extract_ffmpeg(zip_path, install_dir, extract_progress)
            
            if cls._cancel_flag:
                raise Exception("Установка отменена пользователем")
            
            print("Validating installation...")
            if not cls.validate_installation():
                raise Exception("Не все файлы установлены корректно")
            
            ffmpeg_exe = install_dir / "ffmpeg.exe"
            print(f"\n✓ FFmpeg installed: {ffmpeg_exe}")
            print(f"  Size: {ffmpeg_exe.stat().st_size} bytes")
            
            latest_version = cls.FFMPEG_URL.split('/')[-1].replace('.zip', '')
            version_file = install_dir / "version.txt"
            version_file.write_text(latest_version, encoding='utf-8')
            
            date_file = install_dir / "install_date.txt"
            install_date = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
            date_file.write_text(install_date, encoding='utf-8')
            
            zip_path.unlink()
            print(f"Cleaned up: {zip_path}")
            
            print("=" * 60)
            print("Installation complete!")
            print("=" * 60)
            
            log_content = log_buffer.getvalue()
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return True
            
        except Exception as e:
            error_msg = f"Installation error: {e}"
            print(error_msg)
            
            install_dir = cls._get_install_dir()
            if install_dir.exists():
                print(f"Cleaning up after failed installation: {install_dir}")
                shutil.rmtree(install_dir)
            
            import traceback
            traceback.print_exc(file=log_buffer)
            
            log_content = log_buffer.getvalue()
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return False
        finally:
            sys.stdout = old_stdout
    
    @classmethod
    def _download_ffmpeg_windows(cls, progress_callback=None) -> Path:
        """Скачать FFmpeg для Windows с перебором зеркал."""
        temp_dir = Path(tempfile.gettempdir()) / "ffmpeggui_install"
        temp_dir.mkdir(exist_ok=True)
        zip_path = temp_dir / "ffmpeg.zip"
        
        mirrors = cls.MIRROR_URLS.get("windows", [])
        
        for mirror_idx, base_url in enumerate(mirrors):
            print(f"\nTrying mirror {mirror_idx + 1}/{len(mirrors)}: {base_url}")
            cls.FFMPEG_URL = base_url
            
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    print(f"  Download attempt {attempt + 1}/{max_retries}")
                    return cls._download_with_progress(zip_path, progress_callback)
                except Exception as e:
                    print(f"  Attempt {attempt + 1} failed: {e}")
                    if zip_path.exists():
                        zip_path.unlink()
                    if attempt == max_retries - 1:
                        print(f"  Mirror {mirror_idx + 1} failed, trying next...")
                    else:
                        import time
                        time.sleep(2)
                    continue
        
        raise Exception("Не удалось загрузить FFmpeg ни с одного зеркала")
    
    @classmethod
    def _download_with_progress(cls, zip_path: Path, progress_callback=None) -> Path:
        """Загрузить файл с отображением прогресса."""
        print(f"Downloading from: {cls.FFMPEG_URL}")
        
        def report_progress(block_num, block_size, total_size):
            if cls._cancel_flag:
                raise Exception("Установка отменена пользователем")
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, (downloaded / total_size) * 100)
                if progress_callback:
                    progress_callback(percent)
        
        try:
            print("Using urllib.request...")
            urllib.request.urlretrieve(cls.FFMPEG_URL, zip_path, report_progress)
        except Exception as e1:
            print(f"urllib failed: {e1}")
            try:
                import requests
                print("Using requests...")
                response = requests.get(cls.FFMPEG_URL, stream=True, timeout=30)
                response.raise_for_status()
                total = int(response.headers.get('content-length', 0))
                
                with open(zip_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if cls._cancel_flag:
                            raise Exception("Установка отменена")
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total > 0:
                                progress_callback((downloaded / total) * 100)
            except Exception as e2:
                print(f"requests failed: {e2}")
                raise Exception(f"Не удалось загрузить: {e1}")
        
        if not zip_path.exists() or zip_path.stat().st_size == 0:
            raise Exception("Файл не загрузился или пустой")
        
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"Download complete: {size_mb:.1f} MB")
        return zip_path
    
    @classmethod
    def extract_ffmpeg(cls, zip_path: Path, dest_dir: Path, progress_callback=None):
        """Распаковать FFmpeg."""
        print(f"Extracting archive: {zip_path}")
        print(f"Archive size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                members = zip_ref.namelist()
                print(f"Archive contains {len(members)} files")
                
                base_folder = None
                bin_folder = None
                
                for member in members:
                    member_normalized = member.replace('\\', '/')
                    if 'bin/ffmpeg.exe' in member_normalized:
                        parts = member_normalized.split('/')
                        if len(parts) > 1:
                            base_folder = parts[0]
                            bin_folder = f"{base_folder}/bin/"
                            break
                
                print(f"Base folder: {base_folder}")
                print(f"Bin folder: {bin_folder}")
                
                if not base_folder:
                    print("First 10 files in archive:")
                    for m in members[:10]:
                        print(f"  {m}")
                    raise Exception("Не удалось найти bin/ffmpeg.exe в архиве")
                
                members_to_extract = [m for m in members if bin_folder and m.startswith(bin_folder)]
                
                print(f"Extracting {len(members_to_extract)} files from {bin_folder}")
                
                total = len(members_to_extract)
                for i, member in enumerate(members_to_extract):
                    if cls._cancel_flag:
                        raise Exception("Установка отменена пользователем")
                    
                    if member.endswith('/'):
                        continue
                    
                    relative_path = member.replace(bin_folder or '', '').replace('\\', '/')
                    dest_path = dest_dir / relative_path
                    
                    print(f"  Extracting: {member} -> {dest_path}")
                    
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with zip_ref.open(member) as source:
                        with open(dest_path, 'wb') as target:
                            target.write(source.read())
                    
                    if progress_callback:
                        progress_callback((i / total) * 100)
                
                print("Extraction complete")
                for f in dest_dir.iterdir():
                    if f.is_file():
                        print(f"  {f.name} ({f.stat().st_size / (1024*1024):.1f} MB)")
                
        except zipfile.BadZipFile as e:
            print(f"Bad zip file: {e}")
            raise Exception("Архив повреждён. Попробуйте другое зеркало.")
        except Exception as e:
            print(f"Extraction error: {e}")
            raise
    
    @classmethod
    def _install_linux(cls, progress_callback: Optional[Callable] = None) -> bool:
        """Установить FFmpeg на Linux через пакетный менеджер."""
        try:
            from src.platforms import PlatformManager
            plat = PlatformManager.get_platform()
            
            if progress_callback:
                progress_callback("Установка FFmpeg через пакетный менеджер...", 0)
            
            result = plat.install_ffmpeg("", progress_callback)
            
            if result:
                install_dir = cls._get_install_dir()
                install_dir.mkdir(parents=True, exist_ok=True)
                
                version_file = install_dir / "version.txt"
                version_file.write_text("system-package", encoding='utf-8')
                
                date_file = install_dir / "install_date.txt"
                install_date = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
                date_file.write_text(install_date, encoding='utf-8')
                
                return True
            else:
                return False
        except Exception as e:
            print(f"Linux FFmpeg installation error: {e}")
            return False
    
    @classmethod
    def _install_macos(cls, progress_callback: Optional[Callable] = None) -> bool:
        """Установить FFmpeg на macOS через Homebrew."""
        try:
            from src.platforms import PlatformManager
            plat = PlatformManager.get_platform()
            
            if progress_callback:
                progress_callback("Установка FFmpeg через Homebrew...", 0)
            
            result = plat.install_ffmpeg("", progress_callback)
            
            if result:
                install_dir = cls._get_install_dir()
                install_dir.mkdir(parents=True, exist_ok=True)
                
                version_file = install_dir / "version.txt"
                version_file.write_text("homebrew", encoding='utf-8')
                
                date_file = install_dir / "install_date.txt"
                install_date = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
                date_file.write_text(install_date, encoding='utf-8')
                
                return True
            else:
                return False
        except Exception as e:
            print(f"macOS FFmpeg installation error: {e}")
            return False
    
    @classmethod
    def install(cls, progress_callback: Optional[Callable] = None) -> bool:
        """
        Установить FFmpeg (кроссплатформенный метод).
        
        Args:
            progress_callback: Функция обратного вызова (message, percent)
        
        Returns:
            bool: True если установка успешна
        """
        plat = cls._get_platform()
        
        if plat == "windows":
            return cls._install_windows(progress_callback)
        elif plat == "linux":
            return cls._install_linux(progress_callback)
        elif plat == "macos":
            return cls._install_macos(progress_callback)
        else:
            print(f"Unsupported platform: {plat}")
            return False
