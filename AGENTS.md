# FFmpegGUI — правила для агентов разработки

## Команды сборки и запуска

### Запуск приложения
```bash
# Из исходников (разработка)
python src/main_ctk.py

# Или через Python module
python -m src.main_ctk
```

### Сборка EXE
```bash
# Установка зависимостей для сборки
pip install -r requirements.txt
pip install pyinstaller>=6.0.0

# Сборка Windows EXE
python build.py

# Результат: dist/FFmpegConverter.exe
```

### Установка зависимостей
```bash
# Основные зависимости
pip install -r requirements.txt

# Для разработки
pip install -e ".[dev]"

# Для сборки
pip install -e ".[build]"
```

### Линтинг и форматирование
```bash
# Проверка кода (ruff)
ruff check src/

# Авто-исправление
ruff check --fix src/

# Форматирование (black)
black src/

# Проверка форматирования
black --check src/
```

### Тесты
```bash
# Запуск всех тестов
pytest

# Запуск одного теста
pytest tests/test_file.py::test_function_name

# Запуск с покрытием
pytest --cov=src

# Запуск с выводом логов
pytest -v
```

## Структура проекта

```
FFmpegGUI/
├── src/
│   ├── main_ctk.py          # Основное приложение (CustomTkinter)
│   ├── main.py              # Старое приложение (Flet)
│   └── core/
│       ├── ffmpeg.py        # Обёртка для FFmpeg/FFprobe
│       ├── presets.py       # Пресеты конвертации
│       └── ffmpeg_installer.py  # Автоустановка FFmpeg
├── build.py                 # Скрипт сборки PyInstaller
├── requirements.txt         # Зависимости
├── pyproject.toml          # Конфигурация проекта
└── dist/                   # Скомпилированные файлы
```

## Стиль кода

### Импорты
```python
# 1. Стандартные библиотеки
import asyncio
import sys
from pathlib import Path

# 2. Сторонние библиотеки
import customtkinter as ctk
from pydantic import BaseModel

# 3. Локальные импорты
from .core.ffmpeg import FFmpegWrapper
```

### Типизация
- Используйте аннотации типов для всех функций
- Optional для необязательных параметров
- Union для нескольких типов

```python
def convert(file: str, output: str, preset: Optional[Preset] = None) -> bool:
    ...
```

### Именование
- **Классы**: PascalCase (`FFmpegWrapper`, `PresetManager`)
- **Функции**: snake_case (`get_video_info`, `convert_file`)
- **Константы**: UPPER_CASE (`FFMPEG_URL`, `DEFAULT_PRESETS`)
- **Приватные методы**: `_prefix` (`_check_ffmpeg`, `_find_binary`)

### Форматирование
- Длина строки: **100 символов**
- Отступы: **4 пробела** (без табов)
- Кавычки: **двойные** (`"string"`)
- Пробелы вокруг операторов: `x = 5 + 3`

### Обработка ошибок
```python
# Используйте try/except с конкретными исключениями
try:
    result = await ffmpeg.convert(...)
except FileNotFoundError as e:
    log_error(f"FFmpeg не найден: {e}")
    return False
except Exception as e:
    log_error(f"Ошибка конвертации: {e}")
    return False

# Проверка перед использованием
if not ffmpeg_available:
    messagebox.showerror("Ошибка", "FFmpeg не найден")
    return
```

### Dataclasses для структур данных
```python
@dataclass
class Preset:
    id: str
    name: str
    description: str
    video_codec: str
    cq: int = 20
```

## Архитектурные принципы

### UI (CustomTkinter)
- Все виджеты создаются в `create_widgets()`
- Обработчики событий — отдельные методы
- Для долгих операций используйте `threading.Thread`
- Обновление UI из потока: `self.after(0, callback)`

### Core логика
- Бизнес-логика отдельно от UI
- Асинхронные операции для FFmpeg
- Progress callback для отслеживания прогресса

### Установка FFmpeg
- Путь: `%USERPROFILE%\FFmpegGUI\ffmpeg\ffmpeg.exe`
- Проверка: `shutil.which("ffmpeg")` + проверка пути установки
- Автодобавление в PATH через `setx`

## Git правила

### Коммиты
```bash
# Формат: <type>: <description>
git commit -m "fix: исправить ошибку импорта в ffmpeg_installer"
git commit -m "feat: добавить поддержку AMD AMF"
git commit -m "refactor: оптимизировать проверку FFmpeg"
```

### Типы коммитов
- `feat`: новая функциональность
- `fix`: исправление ошибки
- `refactor`: рефакторинг без изменений функциональности
- `docs`: обновление документации
- `build`: изменения сборки

### Ветка
- Основная: `main-FFmpegGUI`
- Перед пушем: `git pull --rebase`

## Частые проблемы

### PyInstaller и импорты
```python
# Для работы в exe используйте:
if getattr(sys, 'frozen', False):
    from src.core.ffmpeg import FFmpegWrapper
else:
    from .core.ffmpeg import FFmpegWrapper
```

### CustomTkinter темы
```python
# Тёмная тема по умолчанию
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Для диалогов:
dialog = ctk.CTkToplevel(self)
dialog.configure(fg_color="#2b2b2b")  # Тёмный фон
```

### Потоки и UI
```python
# НЕ блокируйте главный поток
def start_conversion(self):
    thread = threading.Thread(target=self.run_conversion, daemon=True)
    thread.start()

# Обновляйте UI через after()
self.after(0, lambda: self.label.configure(text="Готово"))
```

## Контакты

Репозиторий: https://github.com/aagarin39/FFmpegGUI.git
Лицензия: MIT
