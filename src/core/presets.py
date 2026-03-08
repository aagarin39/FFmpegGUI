from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass
class Preset:
    id: str
    name: str
    description: str
    video_codec: str
    audio_codec: str = "aac"
    audio_channels: int = 2
    audio_bitrate: str = "192k"
    cq: int = 20
    scale: Optional[str] = None
    remove_subtitles: bool = False
    stabilize: bool = False
    container: str = "mkv"
    extra_args: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "audio_channels": self.audio_channels,
            "audio_bitrate": self.audio_bitrate,
            "cq": self.cq,
            "scale": self.scale,
            "remove_subtitles": self.remove_subtitles,
            "stabilize": self.stabilize,
            "container": self.container,
            "extra_args": self.extra_args,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        return cls(**data)


DEFAULT_PRESETS = [
    Preset(
        id="h264_standard",
        name="H.264 Стандарт",
        description="H.264 NVENC, высокое качество (CQ 20)",
        video_codec="h264_nvenc",
        cq=20,
    ),
    Preset(
        id="h264_light",
        name="H.264 Лёгкий",
        description="H.264 NVENC, 1920x, меньший размер (CQ 30)",
        video_codec="h264_nvenc",
        cq=30,
        scale="1920:-2",
    ),
    Preset(
        id="h264_mp4",
        name="H.264 MP4",
        description="H.264 NVENC, MP4 контейнер, без субтитров",
        video_codec="h264_nvenc",
        cq=20,
        remove_subtitles=True,
        container="mp4",
    ),
    Preset(
        id="h265_standard",
        name="H.265 Стандарт",
        description="HEVC NVENC, высокое качество (CQ 20)",
        video_codec="hevc_nvenc",
        cq=20,
    ),
    Preset(
        id="h265_light",
        name="H.265 Лёгкий",
        description="HEVC NVENC, 1920x, меньший размер (CQ 30)",
        video_codec="hevc_nvenc",
        cq=30,
        scale="1920:-2",
    ),
    Preset(
        id="h265_mp4",
        name="H.265 MP4",
        description="HEVC NVENC, MP4 контейнер, без субтитров",
        video_codec="hevc_nvenc",
        cq=20,
        remove_subtitles=True,
        container="mp4",
    ),
    Preset(
        id="h265_stabilize",
        name="H.265 Стабилизация",
        description="HEVC NVENC со стабилизацией видео",
        video_codec="hevc_nvenc",
        cq=20,
        stabilize=True,
    ),
]


class PresetManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self.presets = DEFAULT_PRESETS.copy()
        self._load_custom_presets()

    def _default_config_path(self) -> str:
        config_dir = Path.home() / ".ffmpeggui"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "presets.json")

    def _load_custom_presets(self):
        if Path(self.config_path).exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for preset_data in data.get("custom_presets", []):
                        preset = Preset.from_dict(preset_data)
                        self.presets.append(preset)
            except (json.JSONDecodeError, IOError):
                pass

    def save_custom_presets(self):
        custom = [p.to_dict() for p in self.presets if p.id not in [dp.id for dp in DEFAULT_PRESETS]]
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"custom_presets": custom}, f, indent=2, ensure_ascii=False)

    def get_preset(self, preset_id: str) -> Optional[Preset]:
        return next((p for p in self.presets if p.id == preset_id), None)

    def add_preset(self, preset: Preset):
        self.presets.append(preset)
        self.save_custom_presets()

    def delete_preset(self, preset_id: str) -> bool:
        if preset_id in [p.id for p in DEFAULT_PRESETS]:
            return False
        self.presets = [p for p in self.presets if p.id != preset_id]
        self.save_custom_presets()
        return True

    def get_all_presets(self) -> list[Preset]:
        return self.presets
