"""
Модуль для автоматической установки FFmpeg.
"""

import sys
import tempfile
import shutil
from pathlib import Path
import urllib.request
import zipfile


class FFmpegInstaller:
    """Установщик FFmpeg для Windows."""
    
    # Текущий URL для загрузки (устанавливается при запуске)
    FFMPEG_URL = ""
    
    # Официальные источники FFmpeg (рекомендованные ffmpeg.org)
    # Порядок: от наиболее надёжного к наименее
    MIRROR_URLS = [
        # GitHub Releases (BtbN) - наиболее надёжный
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        # GitHub Releases (по версии)
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.0.1-win64-gpl.zip",
        # gyan.dev - рекомендован ffmpeg.org
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        # Альтернативный URL gyan.dev
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip",
    ]
    
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
    def get_ffmpeg_version(cls) -> str:
        """Получить версию из файла version.txt"""
        version_file = cls.INSTALL_DIR / "version.txt"
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip()
        return "неизвестно"
    
    @classmethod
    def get_install_date(cls) -> str:
        """Получить дату установки из файла"""
        date_file = cls.INSTALL_DIR / "install_date.txt"
        if date_file.exists():
            return date_file.read_text(encoding='utf-8').strip()
        return "неизвестно"
    
    @classmethod
    def validate_installation(cls) -> bool:
        """Проверить что все файлы на месте"""
        required = ["ffmpeg.exe", "ffprobe.exe"]
        for file in required:
            if not (cls.INSTALL_DIR / file).exists():
                print(f"Missing required file: {file}")
                return False
        
        # Проверка размера (ffmpeg.exe должен быть > 50MB)
        ffmpeg_size = (cls.INSTALL_DIR / "ffmpeg.exe").stat().st_size
        if ffmpeg_size < 50 * 1024 * 1024:
            print(f"ffmpeg.exe too small: {ffmpeg_size} bytes")
            return False
        
        return True
    
    @classmethod
    def rotate_logs(cls):
        """Сдвинуть логи: install.log -> .1 -> .2"""
        log_base = Path.home() / "FFmpegGUI" / "install.log"
        
        # .1 -> .2
        log_2 = log_base.with_suffix('.log.2')
        if log_2.exists():
            log_2.unlink()
        
        log_1 = log_base.with_suffix('.log.1')
        if log_1.exists():
            log_1.rename(log_2)
        
        # current -> .1
        if log_base.exists():
            log_base.rename(log_1)
    
    @classmethod
    def uninstall(cls) -> bool:
        """
        Удалить FFmpeg.
        Возвращает True если успешно.
        """
        try:
            if not cls.INSTALL_DIR.exists():
                return False
            
            print(f"Uninstalling FFmpeg from {cls.INSTALL_DIR}")
            
            # Удаляем ffmpeg папку
            shutil.rmtree(cls.INSTALL_DIR)
            
            # Возвращаем True (не удаляем app/, logs/ — это настройки приложения)
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
    def download_ffmpeg(cls, progress_callback=None) -> Path:
        """Скачать FFmpeg с перебором зеркал и повторными попытками."""
        temp_dir = Path(tempfile.gettempdir()) / "ffmpeggui_install"
        temp_dir.mkdir(exist_ok=True)
        
        zip_path = temp_dir / "ffmpeg.zip"
        
        # Перебираем зеркала
        for mirror_idx, base_url in enumerate(cls.MIRROR_URLS):
            print(f"\nTrying mirror {mirror_idx + 1}/{len(cls.MIRROR_URLS)}: {base_url}")
            cls.FFMPEG_URL = base_url
            
            # Пробуем несколько раз на каждом зеркале
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    print(f"  Download attempt {attempt + 1}/{max_retries}")
                    return cls._download_with_progress(zip_path, progress_callback)
                except Exception as e:
                    print(f"  Attempt {attempt + 1} failed: {e}")
                    # Очищаем неудачный файл
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
        
        # Пробуем urllib
        try:
            print("Using urllib.request...")
            urllib.request.urlretrieve(cls.FFMPEG_URL, zip_path, report_progress)
        except Exception as e1:
            print(f"urllib failed: {e1}")
            # Пробуем requests если есть
            try:
                import requests
                print("Using requests...")
                response = requests.get(cls.FFMPEG_URL, stream=True, timeout=30)
                response.raise_for_status()
                total = int(response.headers.get('content-length', 0))
                
                with open(zip_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
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
                # Проверяем содержимое архива
                members = zip_ref.namelist()
                print(f"Archive contains {len(members)} files")
                
                # Ищем ffmpeg.exe в любой папке bin
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
                    # Выводим первые 10 файлов для отладки
                    print("First 10 files in archive:")
                    for m in members[:10]:
                        print(f"  {m}")
                    raise Exception("Не удалось найти bin/ffmpeg.exe в архиве")
                
                # Распаковываем только bin папку
                members_to_extract = [m for m in members if bin_folder and m.startswith(bin_folder)]
                
                print(f"Extracting {len(members_to_extract)} files from {bin_folder}")
                
                total = len(members_to_extract)
                for i, member in enumerate(members_to_extract):
                    if cls._cancel_flag:
                        raise Exception("Установка отменена пользователем")
                    
                    # Пропускаем директории
                    if member.endswith('/'):
                        print(f"  Skipping directory: {member}")
                        continue
                    
                    # Извлекаем файлы из bin/ прямо в dest_dir
                    relative_path = member.replace(bin_folder or '', '').replace('\\', '/')
                    dest_path = dest_dir / relative_path
                    
                    print(f"  Extracting: {member} -> {dest_path}")
                    
                    # Создаём родительскую директорию если нужно
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Извлекаем
                    with zip_ref.open(member) as source:
                        with open(dest_path, 'wb') as target:
                            target.write(source.read())
                    
                    if progress_callback:
                        progress_callback((i / total) * 100)
                
                print("Extraction complete")
                print(f"Files in {dest_dir}:")
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
    def install(cls, progress_callback=None) -> bool:
        """
        Установить FFmpeg.
        Возвращает True если установка успешна.
        """
        cls.reset_cancel_flag()
        
        # Открываем лог файл
        log_file = Path.home() / "FFmpegGUI" / "install.log"
        log_file.parent.mkdir(exist_ok=True)
        
        # Ротация логов
        cls.rotate_logs()
        
        from io import StringIO
        
        # Перехватываем вывод
        log_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = log_buffer
        
        try:
            print("=" * 60)
            print("FFmpeg Installation Log")
            print("=" * 60)
            print(f"Time: {__import__('datetime').datetime.now()}")
            print(f"Install dir: {cls.INSTALL_DIR}")
            print(f"Mirrors: {len(cls.MIRROR_URLS)}")
            print()
            
            # Очистка старой версии
            if cls.INSTALL_DIR.exists():
                print(f"Cleaning old installation: {cls.INSTALL_DIR}")
                shutil.rmtree(cls.INSTALL_DIR)
            
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
            
            # Проверяем что все файлы на месте
            print("Validating installation...")
            if not cls.validate_installation():
                raise Exception("Не все файлы установлены корректно")
            
            # Проверяем что файл существует
            ffmpeg_exe = cls.INSTALL_DIR / "ffmpeg.exe"
            print(f"\n✓ FFmpeg installed: {ffmpeg_exe}")
            print(f"  Size: {ffmpeg_exe.stat().st_size} bytes")
            
            # Получаем версию из архива (последняя)
            latest_version = cls.FFMPEG_URL.split('/')[-1].replace('.zip', '')
            
            # Сохранение версии и даты
            version_file = cls.INSTALL_DIR / "version.txt"
            version_file.write_text(latest_version, encoding='utf-8')
            print(f"Saved version: {latest_version}")
            
            date_file = cls.INSTALL_DIR / "install_date.txt"
            install_date = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
            date_file.write_text(install_date, encoding='utf-8')
            print(f"Saved install date: {install_date}")
            
            # Очищаем временные файлы
            zip_path.unlink()
            print(f"Cleaned up: {zip_path}")
            
            print("=" * 60)
            print("Installation complete!")
            print("=" * 60)
            
            # Сохраняем лог
            log_content = log_buffer.getvalue()
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return True
            
        except Exception as e:
            error_msg = f"Installation error: {e}"
            print(error_msg)
            
            # Очистка при ошибке
            if cls.INSTALL_DIR.exists():
                print(f"Cleaning up after failed installation: {cls.INSTALL_DIR}")
                shutil.rmtree(cls.INSTALL_DIR)
            
            import traceback
            traceback.print_exc(file=log_buffer)
            
            # Сохраняем лог ошибки
            log_content = log_buffer.getvalue()
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return False
        finally:
            sys.stdout = old_stdout
