import re
import os
import time
from io import BytesIO
from urllib.parse import unquote

import requests
from PIL import Image

RESOLUTIONS = {
    "Low (2048x1024)": (2048, 1024),
    "Medium (4096x2048)": (4096, 2048),
    "High (8192x4096)": (8192, 4096),
    "Max (10240x5120)": (10240, 5120),
}


def extract_pano_id(url: str) -> str | None:
    """Extract panorama ID from a Google Maps URL."""
    match = re.search(r"!1s([^!]+)", url)
    if not match:
        return None
    return match.group(1)


def extract_image_base_url(url: str) -> str | None:
    """Extract the base image URL from the !6s parameter in a Google Maps URL.

    The !6s parameter contains a URL-encoded link to the panorama image on
    Google's CDN (lh3.googleusercontent.com). We decode it and strip the
    size/view params to get the base URL.
    """
    match = re.search(r"!6s([^!]+)", url)
    if not match:
        return None
    encoded_url = match.group(1)
    decoded_url = unquote(encoded_url)
    # Strip size/view params (everything from =w... or =s... onwards)
    base_url = re.sub(r"=w.*$", "", decoded_url)
    base_url = re.sub(r"=s.*$", "", base_url)
    return base_url


def download_panorama(
    image_base_url: str,
    width: int,
    height: int,
    progress_cb=None,
) -> Image.Image:
    """Download the full equirectangular panorama image at the given resolution."""
    url = f"{image_base_url}=w{width}-h{height}"

    if progress_cb:
        progress_cb(0, 1)

    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
            if image.mode != "RGB":
                image = image.convert("RGB")
            if progress_cb:
                progress_cb(1, 1)
            return image
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1)
            else:
                raise


def save_panorama(image: Image.Image, path: str) -> None:
    """Save the stitched panorama as JPEG. Raises FileExistsError if file exists."""
    if os.path.exists(path):
        raise FileExistsError(f"File already exists: {path}")
    image.save(path, "JPEG", quality=95)


def sanitize_filename(name: str) -> str:
    """Remove invalid filesystem characters from a filename."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    cleaned = cleaned.lstrip(".")
    cleaned = cleaned.strip()
    return cleaned if cleaned else "panorama"
