"""
Тесты для модуля platform.
"""
import pytest
import sys
from pathlib import Path

from src.platforms import PlatformManager, Platform
from src.platforms.windows import WindowsPlatform
from src.platforms.linux import LinuxPlatform
from src.platforms.macos import MacOSPlatform


class TestPlatformManager:
    """Тесты для менеджера платформ."""
    
    def test_get_platform_returns_instance(self):
        """Менеджер возвращает экземпляр платформы."""
        platform = PlatformManager.get_platform()
        assert platform is not None
        assert isinstance(platform, Platform)
    
    def test_get_platform_singleton(self):
        """Менеджер возвращает один и тот же экземпляр."""
        platform1 = PlatformManager.get_platform()
        platform2 = PlatformManager.get_platform()
        assert platform1 is platform2
    
    def test_reset_clears_cache(self):
        """Сброс очищает кэш."""
        platform1 = PlatformManager.get_platform()
        PlatformManager.reset()
        platform2 = PlatformManager.get_platform()
        # После сброса должен создаться новый экземпляр
        assert platform1 is not platform2


class TestWindowsPlatform:
    """Тесты для Windows платформы."""
    
    @pytest.fixture
    def platform(self):
        return WindowsPlatform()
    
    def test_name(self, platform):
        """Название платформы."""
        assert platform.name == "windows"
    
    def test_get_ffmpeg_install_path(self, platform):
        """Путь установки FFmpeg."""
        path = platform.get_ffmpeg_install_path()
        assert isinstance(path, Path)
        assert "FFmpegGUI" in str(path)
        assert path.name == "ffmpeg"
    
    def test_get_config_dir(self, platform):
        """Директория конфигурации."""
        config_dir = platform.get_config_dir()
        assert isinstance(config_dir, Path)
        assert "FFmpegGUI" in str(config_dir)
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Только для Windows")
    def test_open_file_explorer(self, platform, tmp_path):
        """Открытие проводника."""
        result = platform.open_file_explorer(tmp_path)
        # Может вернуть False если нет проводника в тестовой среде
        assert isinstance(result, bool)


class TestLinuxPlatform:
    """Тесты для Linux платформы."""
    
    @pytest.fixture
    def platform(self):
        return LinuxPlatform()
    
    def test_name(self, platform):
        """Название платформы."""
        assert platform.name == "linux"
    
    def test_get_ffmpeg_install_path(self, platform):
        """Путь установки FFmpeg."""
        path = platform.get_ffmpeg_install_path()
        assert isinstance(path, Path)
        assert ".local" in str(path)
        assert "FFmpegGUI" in str(path)
    
    def test_get_config_dir_xdg(self, platform, monkeypatch):
        """Директория конфигурации с XDG."""
        monkeypatch.setenv('XDG_CONFIG_HOME', '/custom/config')
        config_dir = platform.get_config_dir()
        # Используем Path для кроссплатформенного сравнения
        assert Path(config_dir).name == "FFmpegGUI"
        assert "config" in str(config_dir)
    
    def test_get_config_dir_default(self, platform, monkeypatch):
        """Директория конфигурации по умолчанию."""
        monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
        config_dir = platform.get_config_dir()
        assert ".config" in str(config_dir)
        assert "FFmpegGUI" in str(config_dir)
    
    def test_is_wayland(self, platform, monkeypatch):
        """Проверка Wayland."""
        monkeypatch.setenv('WAYLAND_DISPLAY', 'wayland-0')
        assert platform.is_wayland() is True
        
        monkeypatch.delenv('WAYLAND_DISPLAY', raising=False)
        assert platform.is_wayland() is False


class TestMacOSPlatform:
    """Тесты для macOS платформы."""
    
    @pytest.fixture
    def platform(self):
        return MacOSPlatform()
    
    def test_name(self, platform):
        """Название платформы."""
        assert platform.name == "macos"
    
    def test_get_ffmpeg_install_path(self, platform):
        """Путь установки FFmpeg."""
        path = platform.get_ffmpeg_install_path()
        assert isinstance(path, Path)
        assert "Applications" in str(path)
        assert "FFmpegGUI" in str(path)
    
    def test_get_config_dir(self, platform):
        """Директория конфигурации."""
        config_dir = platform.get_config_dir()
        assert isinstance(config_dir, Path)
        assert "Library" in str(config_dir)
        assert "Application Support" in str(config_dir)


# Запуск тестов
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
