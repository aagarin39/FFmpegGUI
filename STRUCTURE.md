# Структура проекта FFmpegGUI

## Обзор

Проект разделён на **платформо-независимую** логику (`core/`) и **платформо-специфичную** (`platform/`).

## Структура директорий

```
FFmpegGUI/
├── src/
│   ├── main.py                  # Точка входа (PyQt6 приложение)
│   │
│   ├── core/                    # Платформо-независимая логика
│   │   ├── __init__.py
│   │   ├── ffmpeg.py            # FFmpeg wrapper
│   │   ├── presets.py           # Пресеты конвертации
│   │   ├── ffmpeg_installer.py  # Установка FFmpeg
│   │   ├── ffmpeg_updater.py    # Проверка обновлений
│   │   └── config.py            # Конфигурация приложения ★
│   │
│   ├── platform/                # Платформо-специфичный код ★
│   │   ├── __init__.py          # PlatformManager
│   │   ├── base.py              # Базовый класс Platform
│   │   ├── windows.py           # Windows реализация
│   │   ├── linux.py             # Linux реализация (X11 + Wayland)
│   │   └── macos.py             # macOS реализация
│   │
│   └── ui/                      # Интерфейс (PyQt6)
│       ├── __init__.py
│       └── [будущие компоненты]
│
├── tests/
│   ├── test_platform/           # Тесты платформ
│   │   ├── __init__.py
│   │   └── test_platform.py
│   └── [будущие тесты]
│
├── assets/                      # Ресурсы
│   ├── icons/
│   └── styles/
│
└── [конфигурационные файлы]
```

## Ключевые компоненты

### 1. PlatformManager (`src/platform/__init__.py`)

**Назначение:** Автоматическое определение и предоставление платформы.

```python
from src.platform import PlatformManager

platform = PlatformManager.get_platform()
# Автоматически возвращает:
# - WindowsPlatform() на Windows
# - LinuxPlatform() на Linux  
# - MacOSPlatform() на macOS
```

### 2. Базовый класс Platform (`src/platform/base.py`)

**Назначение:** Определяет интерфейс для всех платформ.

**Методы:**
- `name` — название платформы
- `get_ffmpeg_install_path()` — путь установки FFmpeg
- `install_ffmpeg(url, callback)` — установка FFmpeg
- `add_to_path(path)` — добавление в PATH
- `get_config_dir()` — директория конфигурации
- `open_file_explorer(path)` — открыть файловый менеджер
- `is_wayland()` — проверка Wayland (Linux)

### 3. AppConfig (`src/core/config.py`)

**Назначение:** Централизованное управление конфигурацией.

```python
from src.core.config import get_config

config = get_config()

# Пути (автоматически подстраиваются под платформу)
config.ffmpeg_dir      # Директория FFmpeg
config.ffmpeg_path     # Путь к ffmpeg.exe
config.config_dir      # Директория конфигурации
config.presets_file    # Файл пресетов

# Настройки по умолчанию
config.default_container  # "mkv"
config.default_codec      # "h264"
config.default_cq         # 20
```

## Примеры использования

### Получение пути для FFmpeg

```python
from src.platform import PlatformManager

platform = PlatformManager.get_platform()
ffmpeg_path = platform.get_ffmpeg_install_path()

# Windows: C:\Users\user\FFmpegGUI\ffmpeg
# Linux:   /home/user/.local/FFmpegGUI/bin
# macOS:   /Users/user/Applications/FFmpegGUI
```

### Установка FFmpeg

```python
from src.platform import PlatformManager

platform = PlatformManager.get_platform()

def on_progress(status, percent):
    print(f"{status}: {percent}%")

success = platform.install_ffmpeg(
    url="https://github.com/...",
    progress_callback=on_progress
)
```

### Добавление в PATH

```python
from pathlib import Path
from src.platform import PlatformManager

platform = PlatformManager.get_platform()
ffmpeg_dir = platform.get_ffmpeg_install_path()

platform.add_to_path(ffmpeg_dir)
```

### Конфигурация приложения

```python
from src.core.config import get_config

config = get_config()

# Гарантировать существование директории
config.ensure_config_dir()

# Использовать пути
presets = config.presets_file
ffmpeg = config.ffmpeg_path
```

## Тестирование

### Запуск всех тестов

```bash
pytest
```

### Запуск тестов платформы

```bash
pytest tests/test_platform/ -v
```

### Пример теста

```python
from src.platform import PlatformManager

def test_platform_name():
    platform = PlatformManager.get_platform()
    assert platform.name in ["windows", "linux", "macos"]
```

## Расширение (добавление новой платформы)

1. Создать файл `src/platform/newplatform.py`
2. Унаследовать от `Platform`
3. Реализовать все абстрактные методы
4. Добавить в `src/platform/__init__.py`:

```python
from .newplatform import NewPlatform

# В PlatformManager.get_platform():
if system == "NewOS":
    cls._instance = NewPlatform()
```

## Преимущества структуры

| Аспект | Преимущество |
|--------|--------------|
| **Разделение** | Чёткое разделение на core/ и platform/ |
| **Тестируемость** | Легко мокировать платформо-специфичный код |
| **Расширяемость** | Добавить платформу = создать 1 файл |
| **Сопровождение** | Платформо-независимый код не меняется |
| **Понятность** | Ясно где какая логика находится |

## Миграция

### Старая структура
```
src/
├── main_pyqt.py
└── core/
    └── ffmpeg_installer.py  # Только Windows
```

### Новая структура
```
src/
├── main.py
├── core/                    # Универсальный код
│   └── config.py           # Конфигурация
└── platform/               # Платформы
    ├── windows.py          # Windows
    ├── linux.py            # Linux
    └── macos.py            # macOS
```

## Обратная совместимость

Старые импорты продолжают работать:

```python
# Продолжает работать
from src.core.ffmpeg import FFmpegWrapper
from src.core.presets import PresetManager

# Новый способ (рекомендуется)
from src.platform import PlatformManager
from src.core.config import get_config
```

---

**Статус:** ✅ Реализовано для Windows, 🔄 в разработке для Linux/macOS
