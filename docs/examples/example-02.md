# Example 02: Watermarked export

Apply a transparent PNG watermark during export.

## Prepare assets

1. Create or export a PNG with alpha (recommended width 200–400px).
2. Ensure `ffmpeg` works (`ffmpeg -version`).

## Steps

1. Launch the app: `python main.py`
2. Select an output folder.
3. Paste a direct video URL on any platform tab.
4. Browse to your PNG under **Watermark (PNG)**.
5. Choose **MP4** or **WebM** and start the download.

## Expected result

- Temporary download is processed through moviepy
- Final file is written with the watermark composite
- Progress label reports success per item

## Notes

- Watermark currently stretches to the full frame (center overlay)
- Large source videos take longer because moviepy re-encodes the result
