"""Named batch export presets (audio-only / video+audio / watermark)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class ExportPreset:
    """User-facing export profile applied when enqueueing or batch-updating jobs."""

    id: str
    name: str
    media: str  # video | audio
    output_format: str
    use_watermark: bool
    description: str = ""


# Built-in profiles required by the Suite Download / Queue UX.
AUDIO_ONLY = ExportPreset(
    id="audio_only",
    name="Audio only",
    media="audio",
    output_format="m4a",
    use_watermark=False,
    description="Extract audio (uses AUDIO_FORMAT from settings).",
)
VIDEO_AUDIO = ExportPreset(
    id="video_audio",
    name="Video + audio",
    media="video",
    output_format="mp4",
    use_watermark=False,
    description="Muxed video with audio; no watermark overlay.",
)
WATERMARK = ExportPreset(
    id="watermark",
    name="Watermark",
    media="video",
    output_format="mp4",
    use_watermark=True,
    description="Video + audio with PNG watermark when a path is set.",
)
CUSTOM = ExportPreset(
    id="custom",
    name="Custom",
    media="video",
    output_format="mp4",
    use_watermark=False,
    description="Manual media / container / watermark controls.",
)

BUILTIN_PRESETS: Sequence[ExportPreset] = (AUDIO_ONLY, VIDEO_AUDIO, WATERMARK, CUSTOM)

_BY_ID: Dict[str, ExportPreset] = {p.id: p for p in BUILTIN_PRESETS}


def list_presets(*, include_custom: bool = True) -> List[ExportPreset]:
    """Return built-in presets in display order."""
    if include_custom:
        return list(BUILTIN_PRESETS)
    return [p for p in BUILTIN_PRESETS if p.id != CUSTOM.id]


def get_preset(preset_id: str) -> Optional[ExportPreset]:
    """Lookup a preset by id, or None if unknown."""
    key = (preset_id or "").strip().lower()
    return _BY_ID.get(key)


def resolve_job_options(
    preset: ExportPreset,
    *,
    watermark_path: str = "",
    output_format: str = "",
    media_override: str = "",
) -> Dict[str, str]:
    """
    Resolve per-job download options from a preset + optional UI overrides.

    For Custom, media_override / output_format / watermark_path drive the result.
    Watermark preset requires a non-empty watermark_path to actually overlay.
    """
    if preset.id == CUSTOM.id:
        media = (media_override or "video").strip() or "video"
        fmt = (output_format or ("m4a" if media == "audio" else "mp4")).strip()
        wm = (watermark_path or "").strip() if media == "video" else ""
        return {"media": media, "output_format": fmt, "watermark_path": wm}

    media = preset.media
    if media == "audio":
        fmt = (output_format or preset.output_format or "m4a").strip() or "m4a"
        return {"media": "audio", "output_format": fmt, "watermark_path": ""}

    fmt = (output_format or preset.output_format or "mp4").strip() or "mp4"
    wm = (watermark_path or "").strip() if preset.use_watermark else ""
    return {"media": "video", "output_format": fmt, "watermark_path": wm}


def apply_preset_to_jobs(
    jobs: Iterable[object],
    preset: ExportPreset,
    *,
    watermark_path: str = "",
    output_format: str = "",
) -> int:
    """
    Mutate queued (or any) jobs in-place with resolved preset options.

    Skips search_audio jobs (metadata bridge) — those stay on the audio search path.
    Returns how many jobs were updated.
    """
    updated = 0
    for job in jobs:
        media = getattr(job, "media", "video")
        if media == "search_audio":
            continue
        opts = resolve_job_options(
            preset,
            watermark_path=watermark_path,
            output_format=output_format,
            media_override=media if preset.id == CUSTOM.id else "",
        )
        job.media = opts["media"]
        job.output_format = opts["output_format"]
        job.watermark_path = opts["watermark_path"]
        updated += 1
    return updated
