# FFmpegGUI

Кроссплатформенный конвертер видео и изображений с групповой обработкой файлов.

## Возможности

- **Групповая конвертация** — обработка всех файлов в выбранной папке
- **Пресеты конвертации**:
  - **NVIDIA NVENC**: H.264/H.265 Стандарт/Лёгкий/MP4
  - **Intel QuickSync**: H.264/H.265 Стандарт/Лёгкий
  - **AMD AMF**: H.264/H.265 Стандарт/Лёгкий
- **Конструктор пресетов** — создание собственных пресетов
- **Автоустановка FFmpeg** — загрузка с официального GitHub
- **Прогресс-бар и логирование** — отслеживание процесса конвертации
- **Кроссплатформенность** — Windows, Linux, macOS

## Установка

### Требования

- Python 3.9+
- FFmpeg (устанавливается автоматически или вручную)

### Шаги

```bash
# Клонирование репозитория
git clone https://github.com/aagarin39/FFmpegGUI.git
cd FFmpegGUI

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python src/main_pyqt.py
```

### Автоустановка FFmpeg

При первом запуске приложение предложит автоматически установить FFmpeg:
- Скачивается с [GitHub Releases](https://github.com/BtbN/FFmpeg-Builds/releases)
- Устанавливается в `%USERPROFILE%\FFmpegGUI\ffmpeg`
- Добавляется в PATH пользователя
- Не требует прав администратора

Или установите вручную:
```bash
# Windows: скачайте с https://www.gyan.dev/ffmpeg/builds/
# Linux:
sudo apt install ffmpeg    # Debian/Ubuntu
sudo dnf install ffmpeg    # Fedora

# macOS:
brew install ffmpeg
```

## Структура проекта

```
FFmpegGUI/
├── src/
│   ├── main_pyqt.py         # Основное приложение (PyQt6)
│   └── core/
│       ├── ffmpeg.py        # Обёртка для FFmpeg
│       ├── presets.py       # Управление пресетами
│       └── ffmpeg_installer.py  # Автоустановка FFmpeg
├── build.py                 # Скрипт сборки PyInstaller
├── requirements.txt         # Зависимости
├── pyproject.toml          # Конфигурация проекта
└── dist/                   # Скомпилированные файлы
```

## Пресеты по умолчанию

### NVIDIA NVENC
| Пресет | Описание |
|--------|----------|
| H.264 NVIDIA Стандарт | NVENC, CQ 20, MKV |
| H.264 NVIDIA Лёгкий | NVENC, CQ 30, 1920x, MKV |
| H.264 NVIDIA MP4 | NVENC, CQ 20, MP4, без субтитров |
| H.265 NVIDIA Стандарт | HEVC NVENC, CQ 20, MKV |
| H.265 NVIDIA Лёгкий | HEVC NVENC, CQ 30, 1920x, MKV |
| H.265 NVIDIA MP4 | HEVC NVENC, CQ 20, MP4, без субтитров |

### Intel QuickSync
| Пресет | Описание |
|--------|----------|
| H.264 Intel Стандарт | QSV, CQ 20, MKV |
| H.264 Intel Лёгкий | QSV, CQ 30, 1920x, MKV |
| H.265 Intel Стандарт | HEVC QSV, CQ 20, MKV |
| H.265 Intel Лёгкий | HEVC QSV, CQ 30, 1920x, MKV |

### AMD AMF
| Пресет | Описание |
|--------|----------|
| H.264 AMD Стандарт | AMF, CQ 20, MKV |
| H.264 AMD Лёгкий | AMF, CQ 30, 1920x, MKV |
| H.265 AMD Стандарт | HEVC AMF, CQ 20, MKV |
| H.265 AMD Лёгкий | HEVC AMF, CQ 30, 1920x, MKV |

## Сборка дистрибутива

### Из исходников

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python src/main_pyqt.py
```

### Создание нативного приложения

```bash
# Установка инструментов сборки
pip install -e ".[build]"

# Сборка под вашу платформу
python build.py
```

**Результат:**
- **Windows**: `dist/FFmpegConverter.exe`
- **Linux**: `dist/FFmpegConverter` + `.desktop` файл
- **macOS**: `dist/FFmpegConverter.app`

### Для всех платформ (кросс-компиляция)

Используйте GitHub Actions или CI/CD для сборки под разные платформы:

```bash
# Windows (из Linux через Wine)
# Linux (native)
# macOS (требуется Xcode)
```

## Лицензия

MIT
