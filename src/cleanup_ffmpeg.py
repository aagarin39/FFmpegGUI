"""
FFmpeg Cleanup Utility
Удаляет папку %USERPROFILE%\FFmpegGUI\ с FFmpeg и настройками
"""
import sys
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton,
    QMessageBox, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class CleanupDialog(QDialog):
    """Диалог удаления FFmpeg"""
    
    def __init__(self):
        super().__init__()
        self.ffmpeg_gui_dir = Path.home() / "FFmpegGUI"
        
        self.setWindowTitle("Удалить FFmpeg")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        self._init_ui()
        self._check_ffmpeg()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("🗑️ Удаление FFmpeg")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Описание
        desc = QLabel(
            "Вы уверены что хотите удалить FFmpeg и все данные программы?"
        )
        desc.setStyleSheet("font-size: 13px;")
        layout.addWidget(desc)
        
        # Список что будет удалено
        list_frame = QFrame()
        list_frame.setStyleSheet("background-color: #1f2937; border-radius: 5px; padding: 10px;")
        list_layout = QVBoxLayout(list_frame)
        
        self.items_label = QLabel("Загрузка...")
        self.items_label.setStyleSheet("font-family: Consolas; font-size: 12px; color: #9ca3af;")
        self.items_label.setWordWrap(True)
        list_layout.addWidget(self.items_label)
        
        layout.addWidget(list_frame)
        
        # Предупреждение
        warning_frame = QFrame()
        warning_frame.setStyleSheet("background-color: #fef2f2; border: 1px solid #ef4444; border-radius: 5px; padding: 10px;")
        warning_layout = QVBoxLayout(warning_frame)
        
        warning_label = QLabel("⚠️  Это действие необратимо!\nПрограмма не сможет работать без FFmpeg.")
        warning_label.setStyleSheet("color: #dc2626; font-weight: bold;")
        warning_label.setWordWrap(True)
        warning_layout.addWidget(warning_label)
        
        layout.addWidget(warning_frame)
        
        # Прогресс
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
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
        
        delete_btn = QPushButton("Удалить")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        delete_btn.clicked.connect(self._start_cleanup)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
    
    def _check_ffmpeg(self):
        """Проверить что есть для удаления"""
        if not self.ffmpeg_gui_dir.exists():
            self.items_label.setText("❌ Папка FFmpegGUI не найдена\nНечего удалять.")
            self.items_label.setStyleSheet("color: #ef4444; font-size: 13px;")
            return
        
        # Считаем размер
        total_size = 0
        items = []
        
        for subdir in ["ffmpeg", "app", "logs"]:
            subdir_path = self.ffmpeg_gui_dir / subdir
            if subdir_path.exists():
                size = sum(f.stat().st_size for f in subdir_path.rglob("*") if f.is_file())
                total_size += size
                items.append(f"• {subdir}/ — {size / 1024 / 1024:.1f} MB")
        
        size_text = f"\n".join(items) if items else "Папка пуста"
        total_mb = total_size / 1024 / 1024
        
        self.items_label.setText(f"Будет удалено:\n\n{size_text}\n\nИтого: {total_mb:.1f} MB")
        self.items_label.setStyleSheet("font-family: Consolas; font-size: 12px; color: #9ca3af;")
    
    def _start_cleanup(self):
        """Начать удаление"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены что хотите удалить FFmpeg и все данные?\n\n"
            "Это действие необратимо!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self._cleanup()
    
    def _cleanup(self):
        """Выполнить удаление"""
        try:
            # Показываем прогресс
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)  # Бесконечный прогресс
            
            # Удаляем папку
            if self.ffmpeg_gui_dir.exists():
                shutil.rmtree(self.ffmpeg_gui_dir)
            
            # Скрываем прогресс
            self.progress.setVisible(False)
            
            # Успех
            QMessageBox.information(
                self,
                "Готово",
                "✓ FFmpeg и все данные успешно удалены.\n\n"
                "Освобождено: ~500 MB"
            )
            
            self.accept()
            
        except Exception as e:
            self.progress.setVisible(False)
            
            QMessageBox.critical(
                self,
                "Ошибка",
                f"✗ Не удалось удалить FFmpeg:\n\n{e}"
            )


def main():
    """Точка входа"""
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
    """)
    
    dialog = CleanupDialog()
    result = dialog.exec()
    
    sys.exit(0 if result == QDialog.DialogCode.Accepted else 1)


if __name__ == "__main__":
    main()
