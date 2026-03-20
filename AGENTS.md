# FFmpegGUI — правила для агентов разработки

## Язык общения

**Всё на русском:** вопросы, ответы, сообщения об ошибках в UI.  
**Commit messages — на английском.** Названия переменных/функций — на английском.

## Команды

### Запуск
```bash
python src/main_pyqt.py          # PyQt6 версия (рекомендуется)
```

### Установка зависимостей
```bash
pip install -r requirements.txt  # Основные зависимости
pip install -e ".[dev]"          # Для разработки
pip install -e ".[build]"        # Для сборки
```

### Сборка EXE
```bash
pip install pyinstaller>=6.0.0
python build.py                  # Результат: dist/FFmpegConverter.exe
```

**Важно:** Пользователь получает **ОДИН файл** — `FFmpegConverter.exe`
- `FFmpegConverter.exe` — основная программа (конвертация + очистка FFmpeg)
- `FFmpegConverter_Uninstall.exe` — деинсталлятор (для Панели управления)
- Все функции в одном файле (очистка FFmpeg через `--cleanup-ffmpeg`)

### Линтинг и форматирование
```bash
ruff check src/                  # Проверка кода
ruff check --fix src/            # Авто-исправление
black src/                       # Форматирование
black --check src/               # Проверка форматирования
```

### Тесты
```bash
pytest                           # Запуск всех тестов
pytest tests/test_file.py::test_function_name  # Один тест
pytest --cov=src                 # С покрытием
pytest -v -s tests/test_file.py::test_name     # С отладкой
```

## Стиль кода

### Импорты (3 группы)
```python
# 1. Стандартные библиотеки
import sys
from pathlib import Path

# 2. Сторонние библиотеки
from PyQt6.QtWidgets import QApplication, QMainWindow

# 3. Локальные импорты
from .core.ffmpeg import FFmpegWrapper
```

### Типизация
```python
def convert(file: str, output: str, preset: Optional[Preset] = None) -> bool:
    ...
```

### Именование
- **Классы**: PascalCase (`FFmpegWrapper`, `PresetManager`)
- **Функции**: snake_case (`get_video_info`, `_check_ffmpeg`)
- **Константы**: UPPER_CASE (`FFMPEG_URL`, `INSTALL_DIR`)
- **Приватные**: `_prefix` (`_check_ffmpeg`)

### Форматирование
- Длина строки: **100 символов**
- Отступы: **4 пробела** (без табов)
- Кавычки: **двойные** (`"string"`)
- Blank lines: 2 между функциями/классами, 1 внутри

### Обработка ошибок
```python
try:
    result = ffmpeg.convert(file, output, preset)
except FileNotFoundError as e:
    log_error(f"FFmpeg не найден: {e}")
    return False
except Exception as e:
    log_error(f"Ошибка конвертации: {e}")
    return False
```

### Dataclasses
```python
@dataclass
class Preset:
    id: str
    name: str
    description: str
    hw_accelerator: Optional[str] = None
    codec_type: str = "h264"
    cq: int = 20
    container: str = "mkv"
```

## Архитектура

### UI (PyQt6)
- `QMainWindow` — основной класс
- Layout: `QVBoxLayout`, `QHBoxLayout`, `QFormLayout`
- Долгие операции: `QThread`
- Обновление UI: сигналы/слоты (`pyqtSignal`)
- Стили: `setStyleSheet()` (CSS-подобный)

### Многопоточность
```python
class WorkerThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, int, int)
    
    def run(self):
        for i, item in enumerate(items):
            self.progress.emit(i, item)
        self.finished.emit(True, ok, err)

worker = WorkerThread(...)
worker.progress.connect(self.on_progress)
worker.finished.connect(self.on_done)
worker.start()
```

### Core логика
- Бизнес-логика отдельно от UI
- Синхронные операции для FFmpeg (в потоке)
- Progress callback для отслеживания

### Установка FFmpeg
- Путь: `%USERPROFILE%\FFmpegGUI\ffmpeg\ffmpeg.exe`
- Проверка: `shutil.which("ffmpeg")` + проверка пути
- Автозагрузка: GitHub (BtbN/FFmpeg-Builds)
- Версия: `version.txt`, Дата: `install_date.txt`

## Git

### Коммиты
```bash
git commit -m "feat: добавить поддержку AMD AMF"
git commit -m "fix: исправить ошибку проверки FFmpeg"
git commit -m "refactor: оптимизировать проверку"
git commit -m "docs: обновить AGENTS.md"
```

### Типы коммитов
- `feat`: новая функциональность
- `fix`: исправление ошибки
- `refactor`: рефакторинг
- `docs`: документация
- `build`: сборка
- `ui`: интерфейс
- `test`: тесты
- `chore`: вспомогательные

### Ветка
- Основная: `main-FFmpegGUI`
- Перед пушем: `git pull --rebase`

## Частые проблемы

### PyInstaller импорты
```python
if getattr(sys, 'frozen', False):
    import src.core.ffmpeg
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
else:
    from .core.ffmpeg import FFmpegWrapper
```

### DPI Awareness (Windows)
```python
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        ctypes.windll.user32.SetProcessDPIAware()
```

### PyQt6 стили
```python
app.setStyle("Fusion")
app.setStyleSheet("""
    QWidget { background-color: #111827; color: #f9fafb; }
    QPushButton { background-color: #2563eb; color: white; }
""")
```

### FFmpeg не найден
1. Не установлен → нажать "Установить"
2. Не в PATH → проверить `%USERPROFILE%\FFmpegGUI\ffmpeg`
3. Проблема → удалить и установить заново

## Зависимости

**Основные:** `PyQt6>=6.6.0`, `Pillow>=10.0.0`, `pydantic>=2.0.0`, `requests>=2.31.0`  
**Dev:** `pytest>=7.0.0`, `black>=23.0.0`, `ruff>=0.1.0`  
**Build:** `pyinstaller>=6.0.0`

---
Репозиторий: https://github.com/aagarin39/FFmpegGUI.git | Лицензия: MIT
