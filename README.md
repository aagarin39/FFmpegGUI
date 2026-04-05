# FFmpegGUI

Кроссплатформенная программа для конвертации видео и изображений с графическим интерфейсом.

## Поддерживаемые платформы

| Платформа | Формат | Статус |
|---|---|---|
| **Windows 10/11** | `.exe` (onefile) | ✅ |
| **Linux** (Ubuntu, Fedora, Arch) | Бинарник + `.desktop` | ✅ |
| **macOS 11+** | `.app` bundle | ✅ |

## Что делает

Конвертирует видеофайлы из одного формата в другой:
- MOV → MP4 (для телефона)
- AVI → MKV (чтобы занимало меньше места)
- И ещё 100+ форматов

## Как работает

1. Выбираете видеофайлы
2. Выбираете готовый пресет или настраиваете сами
3. Нажимаете "Конвертировать"

## Готовые настройки

- **Для телефона** — чтобы видео открылось на Android/iPhone
- **Для компьютера** — универсальный формат MP4
- **Сжать файл** — уменьшить размер без потери качества
- **Быстро** — конвертация за минуты
- **Качественно** — максимальное качество

## Особенности

- ✅ Работает быстро (использует видеокарту NVIDIA, Intel или AMD)
- ✅ Не требует интернета (после первой установки)
- ✅ Бесплатно, без рекламы
- ✅ Простой интерфейс
- ✅ Многоязычный интерфейс (Русский / English)
- ✅ Кроссплатформенность

## Установка

### Скачать готовую версию

Скачайте с [GitHub Releases](https://github.com/aagarin39/FFmpegGUI/releases)

| Платформа | Файл |
|---|---|
| Windows | `FFmpegConverter-Windows.exe` |
| Linux | `FFmpegConverter-Linux` |
| macOS | `FFmpegConverter-macOS.app.zip` |

### Или собрать из исходников

```bash
# Клонирование репозитория
git clone https://github.com/aagarin39/FFmpegGUI.git
cd FFmpegGUI

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python src/main_pyqt.py
```

## Первый запуск

При первом запуске программа предложит установить FFmpeg (нужно сделать один раз):

| Платформа | Метод установки |
|---|---|
| **Windows** | Скачивается с GitHub (BtbN/FFmpeg-Builds) |
| **Linux** | Через пакетный менеджер (apt/dnf/pacman) |
| **macOS** | Через Homebrew (`brew install ffmpeg`) |

После установки FFmpeg программа работает без интернета.

## Удаление FFmpeg

- В программе: клик на статус → "Удалить FFmpeg"

## Системные требования

| | Windows | Linux | macOS |
|---|---|---|---|
| **ОС** | Windows 10/11 | Ubuntu 22.04+, Fedora, Arch | macOS 11+ |
| **Память** | 512 MB RAM | 512 MB RAM | 512 MB RAM |
| **Место** | 43 MB (программа) + 580 MB (FFmpeg) | ~40 MB + FFmpeg | ~45 MB + FFmpeg |
| **Видеокарта** | NVIDIA, Intel или AMD | NVIDIA, Intel или AMD | Apple Silicon, Intel + AMD |

## Сборка дистрибутива

```bash
# Установка инструментов сборки
pip install -e ".[build]"

# Сборка (автоматически определяет платформу)
python build.py
```

**Результат:**

| Платформа | Файлы |
|---|---|
| Windows | `dist/FFmpegConverter.exe` |
| Linux | `dist/FFmpegConverter`, `FFmpegConverter.desktop`, `ffmpegconverter.png` |
| macOS | `dist/FFmpegConverter.app` |

## CI/CD

Проект использует GitHub Actions для автоматической сборки:

- При push на `develop` — тесты + сборка на всех 3 платформах
- При создании релиза — автоматическая публикация артефактов
- [Статус сборок](https://github.com/aagarin39/FFmpegGUI/actions)

## Структура проекта

```
FFmpegGUI/
├── src/
│   ├── main_pyqt.py              # Основное приложение (PyQt6)
│   ├── core/                     # Бизнес-логика
│   │   ├── ffmpeg.py             # Конвертация видео
│   │   ├── presets.py            # Пресеты настроек
│   │   └── ffmpeg_installer.py   # Установка FFmpeg (кроссплатформенная)
│   ├── platforms/                # Абстракция платформ (Windows, Linux, macOS)
│   └── i18n/                     # Интернационализация
├── assets/icons/                 # Иконки (.ico, .icns, .png)
├── translations/                 # Файлы переводов (.ts, .qm)
├── tests/                        # Тесты
├── .github/workflows/            # CI/CD конфигурация
├── build.py                      # Скрипт сборки (кроссплатформенный)
└── requirements.txt              # Зависимости
```

## Зависимости

- Python 3.9+
- PyQt6 >= 6.6.0
- requests >= 2.31.0

## Релизы

Текущая версия: **v0.4.0**

- [Скачать последнюю версию](https://github.com/aagarin39/FFmpegGUI/releases)
- [История изменений](https://github.com/aagarin39/FFmpegGUI/releases)

## Лицензия

Apache License 2.0

## Репозиторий

https://github.com/aagarin39/FFmpegGUI.git
