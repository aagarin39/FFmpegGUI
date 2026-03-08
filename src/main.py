import flet as ft
from pathlib import Path
import sys

# Импорт для работы в скомпилированном приложении
if getattr(sys, 'frozen', False):
    # Запуск из exe
    from src.core.ffmpeg import FFmpegWrapper
    from src.core.presets import PresetManager, Preset
else:
    # Запуск из исходников
    try:
        from .core.ffmpeg import FFmpegWrapper
        from .core.presets import PresetManager, Preset
    except ImportError:
        from core.ffmpeg import FFmpegWrapper
        from core.presets import PresetManager, Preset


async def main(page: ft.Page):
    page.title = "FFmpeg Converter"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1200
    page.window.height = 800

    ffmpeg = FFmpegWrapper()
    preset_manager = PresetManager()

    selected_folder = None
    files_list = []
    selected_preset = None
    is_converting = False

    folder_text = ft.Text("Папка не выбрана", size=14, color=ft.Colors.GREY_400)
    files_listview = ft.ListView(expand=True, spacing=10)
    progress_bar = ft.ProgressBar(width=400, visible=False)
    progress_text = ft.Text("", size=12)
    status_text = ft.Text("", size=12, color=ft.Colors.GREEN)
    log_area = ft.TextField(
        multiline=True,
        min_lines=10,
        max_lines=10,
        read_only=True,
        expand=True,
        text_size=12,
    )

    preset_dropdown = ft.Dropdown(
        label="Пресет",
        expand=True,
        options=[ft.dropdown.Option(p.id, p.name) for p in preset_manager.get_all_presets()],
        on_select=lambda e: update_preset_info(e.control.value),
    )

    preset_info = ft.Text("", size=11, color=ft.Colors.GREY_400, italic=True)

    def update_preset_info(preset_id):
        nonlocal selected_preset
        preset = preset_manager.get_preset(preset_id)
        if preset:
            selected_preset = preset
            preset_info.value = preset.description
        page.update()

    def log_message(message: str):
        log_area.value += f"{message}\n"
        log_area.scroll_to_bottom()
        page.update()

    async def pick_folder_click(e):
        nonlocal selected_folder, files_list
        result = await page.get_directory_path_async("Выберите папку с файлами")
        if result:
            selected_folder = result
            folder_text.value = result
            files_list = []
            files_listview.controls.clear()

            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}

            for file in Path(result).iterdir():
                if file.is_file() and file.suffix.lower() in video_extensions | image_extensions:
                    files_list.append(str(file))
                    files_listview.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.VIDEO_FILE, size=20),
                            title=ft.Text(file.name, size=12),
                            subtitle=ft.Text(f"{file.stat().st_size // 1024} KB", size=10),
                        )
                    )

            status_text.value = f"Найдено файлов: {len(files_list)}"
            page.update()

    async def start_conversion(e):
        nonlocal is_converting
        if not selected_folder or not files_list or not selected_preset:
            status_text.value = "Выберите папку и пресет!"
            status_text.color = ft.Colors.RED
            page.update()
            return

        is_converting = True
        convert_button.disabled = True
        progress_bar.visible = True
        page.update()

        output_folder = Path(selected_folder) / "output"
        output_folder.mkdir(exist_ok=True)

        for i, file in enumerate(files_list):
            progress_text.value = f"Файл {i+1}/{len(files_list)}: {Path(file).name}"
            log_message(f"Начало: {Path(file).name}")

            def update_progress(time_str):
                progress_bar.value = float(i) / len(files_list)
                page.update()

            output_ext = selected_preset.container
            output_file = str(output_folder / f"{Path(file).stem}-{selected_preset.video_codec}.{output_ext}")

            try:
                preset_args = ffmpeg.get_preset_args(selected_preset.id)
                success = await ffmpeg.convert(file, output_file, preset_args, update_progress)

                if success:
                    log_message(f"Успешно: {Path(output_file).name}")
                    status_text.value = "Готово!"
                    status_text.color = ft.Colors.GREEN
                else:
                    log_message(f"Ошибка: {Path(file).name}")
                    status_text.value = "Ошибка конвертации"
                    status_text.color = ft.Colors.RED

            except Exception as ex:
                log_message(f"Исключение: {str(ex)}")
                status_text.value = f"Ошибка: {str(ex)}"
                status_text.color = ft.Colors.RED

            progress_bar.value = float(i + 1) / len(files_list)
            page.update()

        is_converting = False
        convert_button.disabled = False
        log_message("=== Конвертация завершена ===")

    convert_button = ft.Button(
        "Конвертировать",
        icon=ft.Icons.PLAY_ARROW,
        on_click=start_conversion,
        disabled=False,
    )

    name_field = ft.TextField(label="Название пресета", expand=True)
    desc_field = ft.TextField(label="Описание", expand=True)
    codec_dropdown = ft.Dropdown(
        label="Видео кодек",
        options=[
            ft.dropdown.Option("h264_nvenc", "H.264 NVENC"),
            ft.dropdown.Option("hevc_nvenc", "H.265 NVENC"),
        ],
        value="h264_nvenc",
        expand=True,
    )
    cq_field = ft.TextField(label="CQ (качество 1-51)", value="20", expand=True)
    scale_dropdown = ft.Dropdown(
        label="Масштабирование",
        options=[
            ft.dropdown.Option("", "Нет"),
            ft.dropdown.Option("1920:-2", "1920x (Full HD)"),
            ft.dropdown.Option("1280:-2", "1280x (HD)"),
            ft.dropdown.Option("3840:-2", "3840x (4K)"),
        ],
        expand=True,
    )
    remove_subs_checkbox = ft.Checkbox(label="Удалить субтитры")
    stabilize_checkbox = ft.Checkbox(label="Стабилизация")
    container_dropdown = ft.Dropdown(
        label="Контейнер",
        options=[
            ft.dropdown.Option("mkv", "MKV"),
            ft.dropdown.Option("mp4", "MP4"),
        ],
        value="mkv",
        expand=True,
    )

    preset_builder_dialog = ft.AlertDialog(
        title=ft.Text("Конструктор пресетов"),
        content=ft.Column([
            name_field,
            desc_field,
            codec_dropdown,
            cq_field,
            scale_dropdown,
            remove_subs_checkbox,
            stabilize_checkbox,
            container_dropdown,
        ], scroll=True),
        actions=[
            ft.TextButton("Отмена", on_click=lambda e: close_dialog()),
            ft.TextButton("Сохранить", on_click=lambda e: save_preset()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def close_dialog():
        preset_builder_dialog.open = False
        page.update()

    def save_preset():
        name = name_field.value
        desc = desc_field.value
        codec = codec_dropdown.value
        cq = int(cq_field.value) if cq_field.value.isdigit() else 20
        scale = scale_dropdown.value if scale_dropdown.value else None
        remove_subs = remove_subs_checkbox.value
        stabilize = stabilize_checkbox.value
        container = container_dropdown.value

        new_preset = Preset(
            id=f"custom_{name.lower().replace(' ', '_')}",
            name=name,
            description=desc,
            video_codec=codec,
            cq=cq,
            scale=scale,
            remove_subtitles=remove_subs,
            stabilize=stabilize,
            container=container,
        )
        preset_manager.add_preset(new_preset)
        preset_dropdown.options.append(ft.dropdown.Option(new_preset.id, new_preset.name))
        close_dialog()
        status_text.value = f"Пресет '{name}' сохранён!"
        status_text.color = ft.Colors.GREEN
        page.update()

    def open_preset_builder(e):
        page.dialog = preset_builder_dialog
        preset_builder_dialog.open = True
        page.update()

    page.add(
        ft.Row([
            ft.Text("FFmpeg Converter", size=24, weight=ft.FontWeight.BOLD),
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=20),
        ft.Row([
            ft.Button(
                "Выбрать папку",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=pick_folder_click,
            ),
            folder_text,
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=10),
        ft.Row([
            preset_dropdown,
            ft.Button("Конструктор", icon=ft.Icons.BUILD, on_click=open_preset_builder),
        ]),
        preset_info,
        ft.Divider(height=10),
        ft.Container(
            content=files_listview,
            border=ft.Border.all(1, ft.Colors.GREY_800),
            border_radius=5,
            padding=10,
            height=200,
            expand=True,
        ),
        ft.Divider(height=10),
        ft.Row([
            convert_button,
            progress_bar,
        ], alignment=ft.MainAxisAlignment.CENTER),
        progress_text,
        status_text,
        ft.Divider(height=10),
        ft.Text("Лог:", size=14, weight=ft.FontWeight.BOLD),
        log_area,
    )


if __name__ == "__main__":
    ft.run(main)
