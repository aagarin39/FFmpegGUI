# FFmpegGUI — правила для агентов разработки

## Язык общения

**Всё взаимодействие с пользователем только на русском языке:**
- Вопросы, уточнения, ответы
- Сообщения об ошибках в UI
- Комментарии в коде (только где необходимо)
- Commit messages — на английском (стандарт Git)
- Названия переменных, функций, классов — на английском

## Команды сборки и запуска

### Запуск приложения

```bash
# PyQt6 версия (рекомендуется)
python src/main_pyqt.py

# CustomTkinter версия (устарела)
python src/main_ctk.py
```

### Установка зависимостей

```bash
# Основные зависимости (PyQt6)
pip install -r requirements.txt

# Для разработки
pip install -e ".[dev]"

# Для сборки
pip install -e ".[build]"
```

### Сборка EXE

```bash
# Установка зависимостей
pip install -r requirements.txt
pip install pyinstaller>=6.0.0

# Сборка Windows EXE
python build.py

# Результат: dist/FFmpegConverter.exe
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
│   ├── main_pyqt.py         # Основное приложение (PyQt6) ★ РЕКОМЕНДУЕТСЯ
│   ├── main_ctk.py          # Устаревшая версия (CustomTkinter)
│   └── core/
│       ├── ffmpeg.py        # Обёртка для FFmpeg/FFprobe
│       ├── presets.py       # Пресеты конвертации
│       ├── ffmpeg_installer.py  # Автоустановка FFmpeg
│       └── ffmpeg_updater.py    # Проверка обновлений
├── build.py                 # Скрипт сборки PyInstaller
├── requirements.txt         # Зависимости
├── pyproject.toml          # Конфигурация проекта
└── dist/                   # Скомпилированные файлы
```

## Стиль кода

### Импорты

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

- Используйте аннотации типов для всех функций
- `Optional` для необязательных параметров
- `Union` для нескольких типов

```python
def convert(file: str, output: str, preset: Optional[Preset] = None) -> bool:
    ...
```

### Именование

- **Классы**: PascalCase (`FFmpegWrapper`, `PresetManager`, `MainWindow`)
- **Функции**: snake_case (`get_video_info`, `convert_file`, `_check_ffmpeg`)
- **Константы**: UPPER_CASE (`FFMPEG_URL`, `DEFAULT_PRESETS`, `INSTALL_DIR`)
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
    result = ffmpeg.convert(file, output, preset)
except FileNotFoundError as e:
    log_error(f"FFmpeg не найден: {e}")
    return False
except Exception as e:
    log_error(f"Ошибка конвертации: {e}")
    return False

# Проверка перед использованием
if not ffmpeg_available:
    status_label.setText("✗ FFmpeg не найден")
    return
```

### Dataclasses для структур данных

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

## Архитектурные принципы

### UI (PyQt6)

- `QMainWindow` как основной класс приложения
- Layout: `QVBoxLayout`, `QHBoxLayout`, `QFormLayout`, `QGridLayout`
- Для долгих операций используйте `QThread`
- Обновление UI через сигналы/слоты: `pyqtSignal`
- Стили через `setStyleSheet()` (CSS-подобный синтаксис)

### UI (CustomTkinter — устарел)

- Все виджеты создаются в `create_widgets()`
- Обработчики событий — отдельные методы
- Для долгих операций используйте `threading.Thread`
- Обновление UI из потока: `self.after(0, callback)`

### Core логика

- Бизнес-логика отдельно от UI
- Синхронные операции для FFmpeg (в потоке)
- Progress callback для отслеживания прогресса

### Установка FFmpeg

- Путь: `%USERPROFILE%\FFmpegGUI\ffmpeg\ffmpeg.exe`
- Проверка: `shutil.which("ffmpeg")` + проверка пути установки
- Автозагрузка с GitHub (BtbN/FFmpeg-Builds)
- Сохранение версии в `version.txt`
- Сохранение даты установки в `install_date.txt`

## Многопоточность

### PyQt6

```python
class WorkerThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, int, int)
    
    def run(self):
        # Фоновая работа
        for i, item in enumerate(items):
            self.progress.emit(i, item)
        self.finished.emit(True, ok, err)

# Использование
worker = WorkerThread(...)
worker.progress.connect(self.on_progress)
worker.finished.connect(self.on_done)
worker.start()
```

### CustomTkinter

```python
def start_conversion(self):
    thread = threading.Thread(target=self._run_conversion, daemon=True)
    thread.start()

def _run_conversion(self):
    # Работа в фоне
    self.after(0, lambda: self.update_ui())
```

## Git правила

### Коммиты

```bash
# Формат: <type>: <description>
git commit -m "fix: исправить ошибку проверки FFmpeg"
git commit -m "feat: добавить поддержку AMD AMF"
git commit -m "refactor: перейти на PyQt6"
git commit -m "docs: обновить AGENTS.md"
```

### Типы коммитов

- `feat`: новая функциональность
- `fix`: исправление ошибки
- `refactor`: рефакторинг без изменений функциональности
- `docs`: обновление документации
- `build`: изменения сборки
- `ui`: изменения интерфейса

### Ветка

- Основная: `main-FFmpegGUI`
- Перед пушем: `git pull --rebase`

## Частые проблемы

### PyInstaller и импорты

```python
# Для работы в exe используйте:
if getattr(sys, 'frozen', False):
    import src.core.ffmpeg
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
else:
    from .core.ffmpeg import FFmpegWrapper
```

### PyQt6 стили

```python
# Тёмная тема через Fusion
app.setStyle("Fusion")
app.setStyleSheet("""
    QWidget {
        background-color: #111827;
        color: #f9fafb;
    }
    QPushButton {
        background-color: #2563eb;
        color: white;
        border-radius: 4px;
        padding: 8px;
    }
""")
```

### DPI Awareness (Windows)

```python
# В начале main():
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor
    except:
        ctypes.windll.user32.SetProcessDPIAware()
```

### FFmpeg не найден

Причины:
1. FFmpeg не установлен → нажать "Установить" в приложении
2. FFmpeg не в PATH → проверить `%USERPROFILE%\FFmpegGUI\ffmpeg`
3. Проблема с установкой → удалить и установить заново

Проверка:
```bash
where ffmpeg
python -c "import shutil; print(shutil.which('ffmpeg'))"
```

## Зависимости

### Основные

- `PyQt6>=6.6.0` — UI framework (рекомендуется)
- `Pillow>=10.0.0` — Работа с изображениями
- `pydantic>=2.0.0` — Валидация данных
- `requests>=2.31.0` — HTTP запросы (загрузка FFmpeg)

### Для разработки

- `pytest>=7.0.0` — Тестирование
- `black>=23.0.0` — Форматирование
- `ruff>=0.1.0` — Линтинг

### Для сборки

- `pyinstaller>=6.0.0` — Компиляция в EXE

## Контакты

Репозиторий: https://github.com/aagarin39/FFmpegGUI.git
Лицензия: MIT
