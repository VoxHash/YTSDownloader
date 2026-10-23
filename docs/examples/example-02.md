# Example 02: Watermarked export

Apply a transparent PNG watermark during export.

## Prepare assets

1. Create or export a PNG with alpha (recommended width 200–400px).
2. Ensure `ffmpeg` works (`ffmpeg -version`).

## Steps

1. Launch the app: `.venv/bin/python main.py` (or `./run.sh`)
2. On **Download**, choose export preset **Watermark**.
3. Select an output folder and browse to your PNG under **Watermark PNG**.
4. Paste a direct video URL → **Resolve & Queue** → **Start Queue**.
5. Or enqueue first, then on **Queue** use **Apply to selected** / **Apply to queued** with the Watermark preset.

## Expected result

- Temporary download is processed through moviepy
- Final file is written with the watermark composite
- Progress label reports success per item

## Notes

- Watermark currently stretches to the full frame (center overlay)
- Large source videos take longer because moviepy re-encodes the result
