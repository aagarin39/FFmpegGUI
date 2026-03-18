"""
Централизованная конфигурация приложения.

Управляет путями, настройками и константами.
"""
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Импорт платформы (абсолютный импорт)
try:
    from src.platform import PlatformManager
except ImportError:
    from platform import PlatformManager


@dataclass
class AppConfig:
    """Конфигурация приложения."""
    
    # Основная информация
    app_name: str = "FFmpeg Converter"
    version: str = "0.1.0"
    organization: str = "aagarin39"
    
    # URL для загрузки FFmpeg
    ffmpeg_github_url: str = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    # Настройки по умолчанию
    default_container: str = "mkv"
    default_codec: str = "h264"
    default_cq: int = 20
    default_audio_channels: int = 2
    
    # Пути (вычисляются)
    _config_dir: Optional[Path] = field(default=None, init=False)
    _presets_file: Optional[Path] = field(default=None, init=False)
    _ffmpeg_dir: Optional[Path] = field(default=None, init=False)
    
    def __post_init__(self):
        """Инициализация путей после создания объекта."""
        platform = PlatformManager.get_platform()
        
        # Директория конфигурации
        self._config_dir = platform.get_config_dir()
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Файл пресетов
        self._presets_file = self._config_dir / "presets.json"
        
        # Директория FFmpeg
        self._ffmpeg_dir = platform.get_ffmpeg_install_path()
    
    @property
    def config_dir(self) -> Path:
        """Директория конфигурации приложения."""
        if self._config_dir is None:
            self.__post_init__()
        return self._config_dir  # type: ignore
    
    @property
    def presets_file(self) -> Path:
        """Файл для хранения пользовательских пресетов."""
        if self._presets_file is None:
            self.__post_init__()
        return self._presets_file  # type: ignore
    
    @property
    def ffmpeg_dir(self) -> Path:
        """Директория установки FFmpeg."""
        if self._ffmpeg_dir is None:
            self.__post_init__()
        return self._ffmpeg_dir  # type: ignore
    
    @property
    def ffmpeg_path(self) -> Path:
        """Полный путь к исполняемому файлу FFmpeg."""
        ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        return self.ffmpeg_dir / ffmpeg_exe
    
    @property
    def ffprobe_path(self) -> Path:
        """Полный путь к исполняемому файлу FFprobe."""
        ffprobe_exe = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
        return self.ffmpeg_dir / ffprobe_exe
    
    def ensure_config_dir(self) -> Path:
        """Гарантировать существование директории конфигурации."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        return self.config_dir


# Глобальный экземпляр конфигурации
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Получить глобальный экземпляр конфигурации.
    
    Returns:
        AppConfig: Конфигурация приложения
    """
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config():
    """Сбросить конфигурацию (для тестов)."""
    global _config
    _config = None


# Экспорт
__all__ = ['AppConfig', 'get_config', 'reset_config']
