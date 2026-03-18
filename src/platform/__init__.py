"""
Модуль платформо-специфичного кода.

Абстракция для работы с различными ОС (Windows, Linux, macOS).
"""
import platform
from typing import Optional

from .base import Platform
from .windows import WindowsPlatform
from .linux import LinuxPlatform
from .macos import MacOSPlatform


class PlatformManager:
    """Менеджер платформ — определяет и возвращает текущую платформу."""
    
    _instance: Optional[Platform] = None
    
    @classmethod
    def get_platform(cls) -> Platform:
        """
        Получить экземпляр платформы для текущей ОС.
        
        Returns:
            Platform: Экземпляр платформо-специфичного класса
        """
        if cls._instance is None:
            system = platform.system()
            
            if system == "Windows":
                cls._instance = WindowsPlatform()
            elif system == "Linux":
                cls._instance = LinuxPlatform()
            elif system == "Darwin":
                cls._instance = MacOSPlatform()
            else:
                raise UnsupportedPlatformError(
                    f"Неподдерживаемая операционная система: {system}"
                )
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Сбросить кэш платформы (для тестов)."""
        cls._instance = None


class UnsupportedPlatformError(Exception):
    """Исключение для неподдерживаемых платформ."""
    pass


# Экспорт для удобного импорта
__all__ = ['PlatformManager', 'Platform', 'UnsupportedPlatformError']
