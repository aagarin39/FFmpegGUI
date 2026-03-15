"""
FFmpeg Converter - PyQt6 версия
Стабильный интерфейс без дерганий на многомониторных системах
"""
import sys
import os
import shutil
import subprocess
import threading
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QFileDialog,
    QScrollArea, QFrame, QMessageBox, QGroupBox, QFormLayout,
    QLineEdit, QCheckBox, QTextEdit, QMenu, QStatusBar, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QAction

# Импорт модулей проекта
if getattr(sys, 'frozen', False):
    import src.core.ffmpeg
    import src.core.ffmpeg_installer
    import src.core.ffmpeg_updater
    import src.core.presets
    
    FFmpegWrapper = src.core.ffmpeg.FFmpegWrapper
    PresetManager = src.core.presets.PresetManager
    Preset = src.core.presets.Preset
    FFmpegInstaller = src.core.ffmpeg_installer.FFmpegInstaller
    FFmpegUpdater = src.core.ffmpeg_updater.FFmpegUpdater
else:
    try:
        from .core.ffmpeg import FFmpegWrapper
        from .core.ffmpeg_installer import FFmpegInstaller
        from .core.ffmpeg_updater import FFmpegUpdater
        from .core.presets import PresetManager, Preset
    except ImportError:
        from core.ffmpeg import FFmpegWrapper
        from core.ffmpeg_installer import FFmpegInstaller
        from core.ffmpeg_updater import FFmpegUpdater
        from core.presets import PresetManager, Preset


class WorkerThread(QThread):
    """Поток для фоновых задач"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, int, int)
    log = pyqtSignal(str)
    
    def __init__(self, files, output_folder, preset, ffmpeg):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.preset = preset
        self.ffmpeg = ffmpeg
    
    def run(self):
        ok = 0
        err = 0
        
        for i, file in enumerate(self.files):
            name = Path(file).name
            self.log.emit(f"▶ {name}")
            
            ext: str = self.preset.container if self.preset.container else "mkv" if self.preset.container else "mkv"
            output = str(self.output_folder / f"{Path(file).stem}.{ext}")
            
            try:
                if self.ffmpeg.convert(file, output, self.preset):
                    ok += 1
                    self.log.emit(f"✓ {name}")
                else:
                    err += 1
                    self.log.emit(f"✗ {name}")
            except Exception as e:
                err += 1
                self.log.emit(f"✗ {name}: {e}")
            
            self.progress.emit(i + 1, name)
        
        self.finished.emit(ok == err == 0, ok, err)


class InstallerThread(QThread):
    """Поток установки FFmpeg"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)
    
    def run(self):
        def cb(status, pct):
            self.progress.emit(int(pct))
        result = FFmpegInstaller.install(cb)
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Converter")
        self.resize(1100, 750)
        self.setMinimumSize(850, 600)
        
        # Центрирование на текущем мониторе
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)
        
        self.ffmpeg = FFmpegWrapper()
        self.preset_manager = PresetManager()
        
        self.selected_folder = None
        self.files_list = []
        self.selected_preset = None
        self.worker = None
        self.installer = None
        
        self._init_ui()
        self._check_ffmpeg()
    
    def _init_ui(self):
        # Центральное окно
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # ===== Header =====
        header = QHBoxLayout()
        
        title = QLabel("FFmpeg Converter")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        self.status_label = QLabel("Проверка...")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # ===== Баннер установки =====
        self.install_banner = QFrame()
        self.install_banner.setStyleSheet("background-color: #d97706; padding: 10px;")
        self.install_banner.hide()
        
        banner_layout = QHBoxLayout(self.install_banner)
        banner_layout.addWidget(QLabel("⚠️  FFmpeg не найден. Установите для работы."))
        
        install_btn = QPushButton("Установить")
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #15803d; color: white;
                padding: 8px 20px; border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #166534; }
        """)
        install_btn.clicked.connect(self._install_ffmpeg)
        banner_layout.addWidget(install_btn)
        banner_layout.addStretch()
        
        layout.addWidget(self.install_banner)
        
        # ===== Баннер обновления =====
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet("background-color: #0284c7; padding: 10px;")
        self.update_banner.hide()
        
        update_layout = QHBoxLayout(self.update_banner)
        update_layout.addWidget(QLabel("🔄 Доступна новая версия FFmpeg"))
        
        update_btn = QPushButton("Обновить")
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #15803d; color: white;
                padding: 8px 15px; border-radius: 4px;
            }
        """)
        update_btn.clicked.connect(self._install_ffmpeg)
        update_layout.addWidget(update_btn)
        
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid white;
                color: white; padding: 5px 10px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        dismiss_btn.clicked.connect(self.update_banner.hide)
        update_layout.addWidget(dismiss_btn)
        update_layout.addStretch()
        
        layout.addWidget(self.update_banner)
        
        # ===== Выбор папки =====
        folder_frame = QGroupBox("Папка с файлами")
        folder_layout = QHBoxLayout(folder_frame)
        
        select_btn = QPushButton("📁 Выбрать папку")
        select_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(select_btn)
        
        self.folder_label = QLabel("Папка не выбрана")
        self.folder_label.setStyleSheet("color: #6b7280;")
        folder_layout.addWidget(self.folder_label)
        folder_layout.addStretch()
        
        layout.addWidget(folder_frame)
        
        # ===== Пресеты =====
        preset_frame = QGroupBox("Настройки конвертации")
        preset_layout = QHBoxLayout(preset_frame)
        
        preset_layout.addWidget(QLabel("Пресет:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(300)
        presets = [p.name for p in self.preset_manager.get_all_presets()]
        self.preset_combo.addItems(presets)
        self.preset_combo.currentTextChanged.connect(self._preset_changed)
        preset_layout.addWidget(self.preset_combo)
        
        builder_btn = QPushButton("🛠 Конструктор")
        builder_btn.clicked.connect(self._preset_builder)
        preset_layout.addWidget(builder_btn)
        
        self.preset_info = QLabel("")
        self.preset_info.setStyleSheet("color: #6b7280; font-style: italic;")
        preset_layout.addWidget(self.preset_info)
        preset_layout.addStretch()
        
        layout.addWidget(preset_frame)
        
        # ===== Список файлов =====
        files_group = QGroupBox("Файлы")
        files_layout = QVBoxLayout(files_group)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setSpacing(2)
        self.files_layout.addStretch()
        
        scroll.setWidget(self.files_container)
        files_layout.addWidget(scroll)
        
        self.files_count = QLabel("Файлов: 0")
        self.files_count.setStyleSheet("color: #6b7280;")
        files_layout.addWidget(self.files_count)
        
        layout.addWidget(files_group, 1)
        
        # ===== Прогресс =====
        progress_group = QGroupBox("Конвертация")
        progress_layout = QHBoxLayout(progress_group)
        
        self.convert_btn = QPushButton("▶ Конвертировать")
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white;
                font-size: 13px; font-weight: bold;
                border-radius: 4px; padding: 10px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #4b5563; }
        """)
        self.convert_btn.clicked.connect(self._convert)
        progress_layout.addWidget(self.convert_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(35)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setMinimumWidth(200)
        self.progress_label.setStyleSheet("color: #6b7280;")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        # ===== Лог =====
        log_group = QGroupBox("Лог операций")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # ===== Статус бар =====
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.convert_status = QLabel("")
        self.statusBar.addWidget(self.convert_status)
    
    def _check_ffmpeg(self):
        self.ffmpeg_available = shutil.which("ffmpeg") is not None
        install_dir = Path.home() / "FFmpegGUI" / "ffmpeg"
        if (install_dir / "ffmpeg.exe").exists():
            self.ffmpeg_available = True
        
        if self.ffmpeg_available:
            self.ffmpeg_version = FFmpegInstaller.get_ffmpeg_version()
            self.status_label.setText(f"✓ FFmpeg {self.ffmpeg_version}")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            self.status_label.mousePressEvent = self._ffmpeg_menu
            self.status_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.install_banner.hide()
            
            # Проверка обновлений через 8 секунд
            QTimer.singleShot(8000, self._check_updates)
        else:
            self.status_label.setText("✗ FFmpeg не найден")
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            self.install_banner.show()
    
    def _check_updates(self):
        try:
            if FFmpegUpdater.should_notify():
                self.update_banner.show()
        except:
            pass
    
    def _ffmpeg_menu(self, event):
        if not self.ffmpeg_available:
            return
        
        menu = QMenu(self)
        menu.addAction(f"✓ FFmpeg {self.ffmpeg_version}")
        menu.addSeparator()
        menu.addAction("📁 Открыть папку", lambda: subprocess.run(["explorer", str(FFmpegInstaller.INSTALL_DIR)]))
        menu.addAction("🗑️ Удалить", self._uninstall_ffmpeg)
        
        menu.exec(self.status_label.mapToGlobal(event.pos()))
    
    def _uninstall_ffmpeg(self):
        if FFmpegInstaller.uninstall():
            self._log("✓ FFmpeg удалён")
            self._check_ffmpeg()
        else:
            self.statusBar.showMessage("✗ Ошибка удаления", 3000)
    
    def _install_ffmpeg(self):
        if self.installer and self.installer.isRunning():
            return
        
        self.update_banner.hide()
        self.installer = InstallerThread()
        self.installer.progress.connect(lambda p: self.statusBar.showMessage(f"Установка... {p}%", 2000))
        self.installer.finished.connect(self._install_done)
        self.installer.start()
    
    def _install_done(self, ok):
        self._check_ffmpeg()
        if ok:
            self._log(f"✓ FFmpeg установлен: {FFmpegInstaller.get_ffmpeg_version()}")
    
    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка с файлами")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(folder)
            self.files_list = []
            
            # Очистка
            while self.files_layout.count() > 1:
                item = self.files_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
                    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            
            for f in Path(folder).iterdir():
                if f.is_file() and f.suffix.lower() in exts:
                    self.files_list.append(str(f))
                    
                    row = QLabel(f"{f.name}  —  {f.stat().st_size // 1024} KB")
                    row.setStyleSheet("padding: 4px; background: #1f2937; border-radius: 3px;")
                    self.files_layout.insertWidget(self.files_layout.count() - 1, row)
            
            self.files_count.setText(f"Файлов: {len(self.files_list)}")
    
    def _preset_changed(self, name):
        p = self.preset_manager.get_preset_by_name(name)
        if p:
            self.selected_preset = p
            self.preset_info.setText(p.description)
    
    def _preset_builder(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Конструктор пресетов")
        dlg.setModal(True)
        dlg.setMinimumWidth(450)
        
        form = QFormLayout()
        
        name = QLineEdit()
        name.setPlaceholderText("Название")
        form.addRow("Название:", name)
        
        desc = QLineEdit()
        desc.setPlaceholderText("Описание")
        form.addRow("Описание:", desc)
        
        hw = QComboBox()
        hw.addItems(["nvenc", "qsv", "amf", "cpu"])
        form.addRow("Ускорение:", hw)
        
        codec = QComboBox()
        codec.addItems(["h264", "hevc"])
        form.addRow("Кодек:", codec)
        
        cq = QLineEdit("20")
        form.addRow("CQ (1-51):", cq)
        
        scale = QComboBox()
        scale.addItems(["", "1920:-2", "1280:-2", "3840:-2"])
        form.addRow("Масштаб:", scale)
        
        audio = QComboBox()
        audio.addItems(["2", "6", "8"])
        form.addRow("Аудио каналы:", audio)
        
        container = QComboBox()
        container.addItems(["mkv", "mp4"])
        form.addRow("Контейнер:", container)
        
        subs = QCheckBox("Удалить субтитры")
        form.addRow("", subs)
        
        btns = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet("background-color: #15803d; color: white; padding: 8px 20px;")
        save_btn.clicked.connect(lambda: self._save_preset(dlg, name, desc, hw, codec, cq, scale, audio, container, subs))
        btns.addWidget(save_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dlg.reject)
        btns.addWidget(cancel_btn)
        
        layout = QVBoxLayout(dlg)
        layout.addLayout(form)
        layout.addLayout(btns)
        
        dlg.exec()
    
    def _save_preset(self, dlg, name, desc, hw, codec, cq, scale, audio, container, subs):
        n = name.text().strip()
        if not n:
            return
        
        h = hw.currentText() if hw.currentText() != "cpu" else None
        p = Preset(
            id=f"custom_{n.lower().replace(' ', '_')}",
            name=n,
            description=desc.text().strip(),
            hw_accelerator=h,
            codec_type=codec.currentText(),
            cq=int(cq.text()) if cq.text().isdigit() else 20,
            scale=scale.currentText() if scale.currentText() else None,
            audio_channels=int(audio.currentText()),
            remove_subtitles=bool(subs.isChecked()),
            container=container.currentText(),
        )
        self.preset_manager.add_preset(p)
        self.preset_combo.addItem(n)
        self._log(f"✓ Пресет: {n}")
        dlg.accept()
    
    def _convert(self):
        if not self.ffmpeg_available:
            self.convert_status.setText("✗ FFmpeg не найден")
            self.convert_status.setStyleSheet("color: #ef4444;")
            return
        if not self.files_list:
            self.convert_status.setText("⚠️ Нет файлов")
            self.convert_status.setStyleSheet("color: #f59e0b;")
            return
        if not self.selected_preset:
            self.convert_status.setText("⚠️ Нет пресета")
            self.convert_status.setStyleSheet("color: #f59e0b;")
            return
        
        self.convert_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.convert_status.setText("Конвертация...")
        self.convert_status.setStyleSheet("color: #f59e0b;")
        
        out = Path(self.selected_folder) / "output"
        out.mkdir(exist_ok=True)
        
        self.worker = WorkerThread(self.files_list, out, self.selected_preset, self.ffmpeg)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_done)
        self.worker.log.connect(self._log)
        self.worker.start()
    
    def _on_progress(self, current, name):
        self.progress_bar.setValue(int(current / len(self.files_list) * 100))
        self.progress_label.setText(name)
    
    def _on_done(self, ok, err):
        self.convert_btn.setEnabled(True)
        total = ok + err
        if err == 0:
            self.convert_status.setText(f"✓ Готово: {ok}/{total}")
            self.convert_status.setStyleSheet("color: #22c55e;")
        else:
            self.convert_status.setText(f"⚠️ {ok} успешно, {err} ошибок")
            self.convert_status.setStyleSheet("color: #f59e0b;")
        self._log(f"=== {ok} успешно, {err} ошибок ===")
    
    def _log(self, msg):
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {msg}")


# Импорт QTimer в начале файла


def main():
    # Настройка DPI
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            pass
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Тёмная тема
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #111827;
            color: #f9fafb;
            font-family: "Segoe UI";
            font-size: 13px;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #374151;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QComboBox, QLineEdit, QTextEdit {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 4px;
            padding: 6px;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QScrollBar:vertical {
            background: #1f2937;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #4b5563;
            border-radius: 5px;
        }
        QProgressBar {
            background: #1f2937;
            border: none;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #2563eb;
            border-radius: 4px;
        }
    """)
    
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
