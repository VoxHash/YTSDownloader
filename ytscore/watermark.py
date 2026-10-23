"""Optional full-frame watermark composite."""

from __future__ import annotations

import numpy as np
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image


def add_watermark(video_path: str, watermark_path: str, output_path: str) -> str:
    try:
        with VideoFileClip(video_path) as video:
            video_width, video_height = video.size
            watermark = Image.open(watermark_path).convert("RGBA")
            watermark = watermark.resize((video_width, video_height), Image.LANCZOS)
            watermark_array = np.array(watermark)
            watermark_clip = ImageClip(watermark_array).with_duration(video.duration).with_opacity(1)
            final_video = CompositeVideoClip(
                [video.with_audio(video.audio), watermark_clip.with_position(("center", "center"))]
            )
            if output_path.endswith(".mp4"):
                codec, audio_codec = "libx264", "aac"
            elif output_path.endswith(".webm"):
                codec, audio_codec = "libvpx", "libvorbis"
            else:
                raise ValueError("Unsupported output format")
            final_video.write_videofile(
                output_path, codec=codec, audio_codec=audio_codec, fps=24
            )
            return "Video processed successfully."
    except Exception as e:
        return f"Error adding watermark: {str(e)}"
