# 360downloader
A desktop GUI application that downloads 360-degree panorama images from Google Maps, stitches the tiles into a single equirectangular image, and saves it locally.

## Technology Stack

- **Language:** Python 3
- **GUI Framework:** CustomTkinter
- **Image Processing:** Pillow
- **HTTP:** requests
- **Threading:** standard library `threading`

## Architecture

Three source files:

- **`main.py`** - Entry point, launches the GUI
- **`gui.py`** - CustomTkinter window with all UI elements and event handlers
- **`panorama.py`** - URL parsing, tile downloading, image stitching (no GUI dependencies; accepts a progress callback from `gui.py` for reporting progress)

## GUI Layout

Single window titled "360 Downloader", vertical layout:

1. **URL Input** - Label + text entry for pasting a Google Maps link
2. **Resolution Selector** - Dropdown with presets:
   - Low (2048x1024) - zoom 2, 4x2 tiles
   - Medium (4096x2048) - zoom 3, 8x4 tiles
   - High (8192x4096) - zoom 4, 16x8 tiles
   - Max (13312x6656) - zoom 5, 26x13 tiles
3. **Download Folder** - Text field + "Browse" button (opens directory picker)
4. **Filename** - Text entry (without extension; app appends `.jpg`). Defaults to the panorama ID. Invalid filesystem characters are stripped. If the file already exists in the download folder, show a warning in the status label and do not overwrite.
5. **Download Button** - Triggers download
6. **Progress Bar** - Shows download/stitching progress
7. **Status Label** - Text feedback (progress messages, errors, completion)

**Defaults:**
- Resolution: High (8192x4096)
- Download folder: user's home directory

## Panorama Download Logic

### URL Parsing

Only long-form Google Maps URLs are supported (not short links like `goo.gl/maps/...`).

Extract the panorama ID using the regex pattern: `!1s([^!]+)` — the ID is the capture group between `!1s` and the next `!` character. Pano IDs consist of alphanumeric characters plus `-` and `_`. Example: from the sample URL, the panorama ID is `CIHM0ogKEICAgICGvNbNRQ`.

Validation: if no panorama ID is found, display an error in the status label.

### Tile Download

Tiles are downloaded in parallel using `concurrent.futures.ThreadPoolExecutor` with 8 workers for faster downloads at higher zoom levels. All HTTP requests use a 10-second timeout. If any single tile fails after retries, the entire download is aborted (fail-fast) and remaining futures are cancelled.

Tiles are fetched from Google's tile server:

```
https://cbk0.google.com/cbk?output=tile&panoid={pano_id}&zoom={zoom}&x={col}&y={row}
```

Each tile is 512x512 pixels. The tile grid dimensions per zoom level:

| Zoom | Columns x Rows | Output Size |
|------|----------------|-------------|
| 2    | 4x2            | 2048x1024   |
| 3    | 8x4            | 4096x2048   |
| 4    | 16x8           | 8192x4096   |
| 5    | 26x13          | 13312x6656  |

### Image Stitching

Using Pillow:
1. Create a blank image of the full output size
2. Paste each downloaded tile at position `(col * 512, row * 512)`
3. Save as JPEG with `quality=95` to avoid compression artifacts on large images

### Threading

Download runs in a background thread to keep the GUI responsive. `panorama.py` accepts a progress callback function. `gui.py` provides a callback that wraps updates in `root.after()` to ensure thread-safe GUI updates. This keeps `panorama.py` free of any GUI dependencies.

The download button is disabled while a download is in progress to prevent concurrent downloads.

### Error Handling

- Invalid/unparseable URL: show error in status label
- Network failure on a tile: retry up to 3 times with 1-second delay between retries, then show error
- Missing panorama ID: show error in status label
- All errors displayed in the status label, no crashes

## Scope Exclusions

- No preview of the panorama
- No batch/queue mode
- No download history
- No custom resolution input
