"""
FFmpeg Converter Uninstaller

Стандартная логика:
1. Установить → 2. Пользоваться → 3. Удалить если не нужно
"""
import sys
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class UninstallDialog(QDialog):
    """Диалог удаления FFmpeg Converter"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Удаление FFmpeg Converter")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        # Пути
        self.app_dir = Path.home() / "FFmpegGUI"
        self.ffmpeg_dir = self.app_dir / "ffmpeg"
        self.app_data_dir = self.app_dir / "app"
        self.logs_dir = self.app_dir / "logs"
        
        # Путь к exe (для удаления)
        self.exe_path = Path(sys.executable)
        
        self._init_ui()
        self._check_components()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("🗑️ Удаление FFmpeg Converter")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Описание
        desc = QLabel(
            "Выберите компоненты для удаления.\n"
            "Это действие необратимо!"
        )
        desc.setStyleSheet("color: #ef4444; font-size: 13px;")
        layout.addWidget(desc)
        
        # Компоненты
        components_group = QGroupBox("Компоненты")
        components_layout = QVBoxLayout(components_group)
        
        # Программа (всегда выбрана)
        self.cb_program = QCheckBox("Программа (FFmpegConverter.exe)")
        self.cb_program.setChecked(True)
        self.cb_program.setEnabled(False)  # Нельзя снять
        self.cb_program.setStyleSheet("font-weight: bold;")
        components_layout.addWidget(self.cb_program)
        
        # FFmpeg
        self.cb_ffmpeg = QCheckBox("FFmpeg (~/FFmpegGUI/ffmpeg/)")
        self.cb_ffmpeg.setChecked(False)
        self.cb_ffmpeg.setStyleSheet("color: #9ca3af;")
        components_layout.addWidget(self.cb_ffmpeg)
        
        # Настройки и пресеты
        self.cb_settings = QCheckBox("Настройки и пресеты (~/FFmpegGUI/app/)")
        self.cb_settings.setChecked(True)
        components_layout.addWidget(self.cb_settings)
        
        # Логи
        self.cb_logs = QCheckBox("Логи установки (~/FFmpegGUI/logs/)")
        self.cb_logs.setChecked(True)
        components_layout.addWidget(self.cb_logs)
        
        layout.addWidget(components_group)
        
        # Предупреждение
        warning_frame = QFrame()
        warning_frame.setStyleSheet("background-color: #fef2f2; border: 1px solid #ef4444; border-radius: 5px; padding: 10px;")
        warning_layout = QVBoxLayout(warning_frame)
        
        warning_label = QLabel("⚠️  Удалённые компоненты не смогут быть восстановлены!")
        warning_label.setStyleSheet("color: #dc2626; font-weight: bold;")
        warning_layout.addWidget(warning_label)
        
        layout.addWidget(warning_frame)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #4b5563;
                padding: 8px 20px;
                border-radius: 4px;
                color: #f9fafb;
            }
            QPushButton:hover { background-color: #374151; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        uninstall_btn = QPushButton("Удалить")
        uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        uninstall_btn.clicked.connect(self._start_uninstall)
        btn_layout.addWidget(uninstall_btn)
        
        layout.addLayout(btn_layout)
    
    def _check_components(self):
        """Проверить что установлено"""
        # FFmpeg
        if self.ffmpeg_dir.exists():
            self.cb_ffmpeg.setText(f"FFmpeg (~/FFmpegGUI/ffmpeg/) — установлен")
            self.cb_ffmpeg.setStyleSheet("")
        else:
            self.cb_ffmpeg.setText("FFmpeg — не установлен")
            self.cb_ffmpeg.setEnabled(False)
            self.cb_ffmpeg.setStyleSheet("color: #6b7280;")
        
        # Настройки
        if self.app_data_dir.exists():
            presets_count = len(list(self.app_data_dir.glob("*.json")))
            self.cb_settings.setText(f"Настройки и пресеты ({presets_count} файлов)")
        else:
            self.cb_settings.setEnabled(False)
            self.cb_settings.setStyleSheet("color: #6b7280;")
        
        # Логи
        if self.logs_dir.exists():
            logs_count = len(list(self.logs_dir.glob("*.log*")))
            self.cb_logs.setText(f"Логи установки ({logs_count} файлов)")
        else:
            self.cb_logs.setEnabled(False)
            self.cb_logs.setStyleSheet("color: #6b7280;")
    
    def _start_uninstall(self):
        """Начать удаление"""
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены что хотите удалить выбранные компоненты?\n\n"
            "Это действие необратимо!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Выполняем удаление
        self._uninstall()
    
    def _uninstall(self):
        """Выполнить удаление"""
        results = []
        
        # 1. FFmpeg
        if self.cb_ffmpeg.isChecked() and self.ffmpeg_dir.exists():
            try:
                shutil.rmtree(self.ffmpeg_dir)
                results.append("✓ FFmpeg удалён")
            except Exception as e:
                results.append(f"✗ Ошибка удаления FFmpeg: {e}")
        
        # 2. Настройки
        if self.cb_settings.isChecked() and self.app_data_dir.exists():
            try:
                shutil.rmtree(self.app_data_dir)
                results.append("✓ Настройки удалены")
            except Exception as e:
                results.append(f"✗ Ошибка удаления настроек: {e}")
        
        # 3. Логи
        if self.cb_logs.isChecked() and self.logs_dir.exists():
            try:
                shutil.rmtree(self.logs_dir)
                results.append("✓ Логи удалены")
            except Exception as e:
                results.append(f"✗ Ошибка удаления логов: {e}")
        
        # 4. Программа (если не из devenv)
        if self.cb_program.isChecked():
            if getattr(sys, 'frozen', False):
                try:
                    # Пытаемся удалить exe и связанные файлы
                    exe_dir = self.exe_path.parent
                    for file in exe_dir.glob("*"):
                        if file.is_file():
                            file.unlink()
                    # Пытаемся удалить пустую директорию
                    if not any(exe_dir.iterdir()):
                        exe_dir.rmdir()
                    results.append("✓ Программа удалена")
                except Exception as e:
                    results.append(f"⚠️ Программа будет удалена после перезапуска: {e}")
            else:
                results.append("ℹ️ Запуск из разработки — программа не удаляется")
        
        # Показываем результат
        result_text = "\n".join(results)
        QMessageBox.information(
            self,
            "Удаление завершено",
            f"Результат удаления:\n\n{result_text}"
        )
        
        self.accept()


def main():
    """Точка входа деинсталлятора"""
    app = QApplication(sys.argv)
    
    # Тёмная тема
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QDialog, QWidget {
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
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
    """)
    
    dialog = UninstallDialog()
    result = dialog.exec()
    
    sys.exit(0 if result == QDialog.DialogCode.Accepted else 1)


if __name__ == "__main__":
    main()
