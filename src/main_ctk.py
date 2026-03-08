import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import asyncio
import sys

try:
    from .core.ffmpeg import FFmpegWrapper
    from .core.presets import PresetManager, Preset
except ImportError:
    from core.ffmpeg import FFmpegWrapper
    from core.presets import PresetManager, Preset


class ConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FFmpeg Converter")
        self.geometry("1000x700")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.ffmpeg = FFmpegWrapper()
        self.preset_manager = PresetManager()

        self.selected_folder = None
        self.files_list = []
        self.selected_preset = None
        self.is_converting = False

        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(
            self,
            text="FFmpeg Converter",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=20, padx=20)

        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        self.btn_select_folder = ctk.CTkButton(
            folder_frame,
            text="Выбрать папку",
            command=self.select_folder,
            width=150
        )
        self.btn_select_folder.grid(row=0, column=0, padx=10, pady=10)

        self.lbl_folder = ctk.CTkLabel(
            folder_frame,
            text="Папка не выбрана",
            text_color="gray"
        )
        self.lbl_folder.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        preset_frame = ctk.CTkFrame(self)
        preset_frame.grid(row=2, column=0, pady=10, padx=20, sticky="ew")

        self.preset_var = ctk.StringVar(value="")
        preset_names = [p.name for p in self.preset_manager.get_all_presets()]
        
        self.cmb_preset = ctk.CTkComboBox(
            preset_frame,
            values=preset_names,
            variable=self.preset_var,
            command=self.on_preset_change,
            width=300
        )
        self.cmb_preset.grid(row=0, column=0, padx=10, pady=10)

        self.btn_preset_builder = ctk.CTkButton(
            preset_frame,
            text="Конструктор",
            command=self.open_preset_builder,
            width=150
        )
        self.btn_preset_builder.grid(row=0, column=1, padx=10, pady=10)

        self.lbl_preset_info = ctk.CTkLabel(
            preset_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.lbl_preset_info.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=3, column=0, pady=10, padx=20, sticky="nsew")

        self.files_listbox = ctk.CTkScrollableFrame(files_frame)
        self.files_listbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_file_count = ctk.CTkLabel(
            files_frame,
            text="Файлов: 0",
            text_color="gray"
        )
        self.lbl_file_count.pack(padx=10, pady=5, anchor="w")

        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=4, column=0, pady=10, padx=20, sticky="ew")

        self.btn_convert = ctk.CTkButton(
            progress_frame,
            text="Конвертировать",
            command=self.start_conversion,
            width=200,
            height=40
        )
        self.btn_convert.grid(row=0, column=0, padx=10, pady=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(1, weight=1)

        self.lbl_progress = ctk.CTkLabel(progress_frame, text="")
        self.lbl_progress.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.lbl_status = ctk.CTkLabel(progress_frame, text="", text_color="green")
        self.lbl_status.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=5, column=0, pady=10, padx=20, sticky="ew")

        ctk.CTkLabel(
            log_frame,
            text="Лог:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.log_text = ctk.CTkTextbox(log_frame, height=100, state="disabled")
        self.log_text.pack(fill="x", padx=10, pady=10)

    def log_message(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с файлами")
        if folder:
            self.selected_folder = folder
            self.lbl_folder.configure(text=folder)
            self.files_list = []

            for widget in self.files_listbox.winfo_children():
                widget.destroy()

            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}

            for file in Path(folder).iterdir():
                if file.is_file() and file.suffix.lower() in video_extensions | image_extensions:
                    self.files_list.append(str(file))
                    file_frame = ctk.CTkFrame(self.files_listbox)
                    file_frame.pack(fill="x", pady=2)
                    
                    ctk.CTkLabel(
                        file_frame,
                        text=file.name,
                        width=600,
                        anchor="w"
                    ).pack(side="left", padx=10, pady=5)
                    
                    ctk.CTkLabel(
                        file_frame,
                        text=f"{file.stat().st_size // 1024} KB",
                        text_color="gray",
                        width=100
                    ).pack(side="right", padx=10, pady=5)

            self.lbl_file_count.configure(text=f"Файлов: {len(self.files_list)}")

    def on_preset_change(self, value):
        preset = self.preset_manager.get_preset_by_name(value)
        if preset:
            self.selected_preset = preset
            self.lbl_preset_info.configure(text=preset.description)

    def open_preset_builder(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Конструктор пресетов")
        dialog.geometry("500x600")
        dialog.transient(self)

        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dialog, text="Название пресета:").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        name_entry = ctk.CTkEntry(dialog)
        name_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(dialog, text="Описание:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        desc_entry = ctk.CTkEntry(dialog)
        desc_entry.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(dialog, text="Видео кодек:").grid(row=4, column=0, padx=20, pady=10, sticky="w")
        codec_var = ctk.StringVar(value="h264_nvenc")
        codec_combo = ctk.CTkComboBox(
            dialog,
            values=["h264_nvenc", "hevc_nvenc"],
            variable=codec_var
        )
        codec_combo.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(dialog, text="CQ (качество 1-51):").grid(row=6, column=0, padx=20, pady=10, sticky="w")
        cq_entry = ctk.CTkEntry(dialog)
        cq_entry.insert(0, "20")
        cq_entry.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(dialog, text="Масштабирование:").grid(row=8, column=0, padx=20, pady=10, sticky="w")
        scale_var = ctk.StringVar(value="")
        scale_combo = ctk.CTkComboBox(
            dialog,
            values=["", "1920:-2", "1280:-2", "3840:-2"],
            variable=scale_var
        )
        scale_combo.grid(row=9, column=0, padx=20, pady=5, sticky="ew")

        remove_subs_var = ctk.BooleanVar()
        ctk.CTkCheckBox(dialog, text="Удалить субтитры", variable=remove_subs_var).grid(
            row=10, column=0, padx=20, pady=10, sticky="w"
        )

        stabilize_var = ctk.BooleanVar()
        ctk.CTkCheckBox(dialog, text="Стабилизация", variable=stabilize_var).grid(
            row=11, column=0, padx=20, pady=10, sticky="w"
        )

        ctk.CTkLabel(dialog, text="Контейнер:").grid(row=12, column=0, padx=20, pady=10, sticky="w")
        container_var = ctk.StringVar(value="mkv")
        container_combo = ctk.CTkComboBox(
            dialog,
            values=["mkv", "mp4"],
            variable=container_var
        )
        container_combo.grid(row=13, column=0, padx=20, pady=5, sticky="ew")

        def save_preset():
            name = name_entry.get()
            desc = desc_entry.get()
            cq = int(cq_entry.get()) if cq_entry.get().isdigit() else 20

            new_preset = Preset(
                id=f"custom_{name.lower().replace(' ', '_')}",
                name=name,
                description=desc,
                video_codec=codec_var.get(),
                cq=cq,
                scale=scale_var.get() if scale_var.get() else None,
                remove_subtitles=remove_subs_var.get(),
                stabilize=stabilize_var.get(),
                container=container_var.get(),
            )
            self.preset_manager.add_preset(new_preset)
            
            current = list(self.cmb_preset.cget("values"))
            current.append(name)
            self.cmb_preset.configure(values=current)
            
            self.log_message(f"Пресет '{name}' сохранён!")
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.grid(row=14, column=0, padx=20, pady=20, sticky="e")

        ctk.CTkButton(btn_frame, text="Отмена", command=lambda: dialog.destroy()).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Сохранить", command=save_preset).pack(side="right", padx=5)

    def start_conversion(self):
        if not self.selected_folder or not self.files_list or not self.selected_preset:
            messagebox.showwarning("Внимание", "Выберите папку и пресет!")
            return

        self.is_converting = True
        self.btn_convert.configure(state="disabled")
        self.progress_bar.set(0)

        thread = threading.Thread(target=self.run_conversion, daemon=True)
        thread.start()

    def run_conversion(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            output_folder = Path(self.selected_folder) / "output"
            output_folder.mkdir(exist_ok=True)

            for i, file in enumerate(self.files_list):
                self.lbl_progress.configure(text=f"Файл {i+1}/{len(self.files_list)}: {Path(file).name}")
                self.log_message(f"Начало: {Path(file).name}")

                output_ext = self.selected_preset.container
                output_file = str(output_folder / f"{Path(file).stem}-{self.selected_preset.video_codec}.{output_ext}")

                try:
                    preset_args = self.ffmpeg.get_preset_args(self.selected_preset.id)
                    success = loop.run_until_complete(
                        self.ffmpeg.convert(file, output_file, preset_args)
                    )

                    if success:
                        self.log_message(f"Успешно: {Path(output_file).name}")
                        self.lbl_status.configure(text="Готово!", text_color="green")
                    else:
                        self.log_message(f"Ошибка: {Path(file).name}")
                        self.lbl_status.configure(text="Ошибка конвертации", text_color="red")

                except Exception as ex:
                    self.log_message(f"Исключение: {str(ex)}")
                    self.lbl_status.configure(text=f"Ошибка: {str(ex)}", text_color="red")

                self.progress_bar.set(float(i + 1) / len(self.files_list))

            self.log_message("=== Конвертация завершена ===")

        finally:
            loop.close()
            self.is_converting = False
            self.btn_convert.configure(state="normal")


if __name__ == "__main__":
    app = ConverterApp()
    app.mainloop()
