import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from src.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

logger = logging.getLogger(__name__)

UPLOAD_URL = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"


def _generate_signature(params: dict) -> str:
    """Generate Cloudinary API signature from params + secret."""
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    to_sign = sorted_params + CLOUDINARY_API_SECRET
    return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()


def upload_image(image_url: str, folder: str = "dira-bot") -> str | None:
    """Upload an image URL to Cloudinary. Returns the permanent URL or None on failure."""
    if not CLOUDINARY_CLOUD_NAME:
        return None

    try:
        timestamp = str(int(time.time()))
        params = {"folder": folder, "timestamp": timestamp}
        signature = _generate_signature(params)

        resp = requests.post(
            UPLOAD_URL,
            data={
                "file": image_url,
                "folder": folder,
                "timestamp": timestamp,
                "api_key": CLOUDINARY_API_KEY,
                "signature": signature,
            },
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            return data.get("secure_url")
        else:
            logger.debug("Cloudinary upload failed (%d): %s", resp.status_code, resp.text[:200])
            return None

    except Exception as e:
        logger.debug("Cloudinary upload error: %s", e)
        return None


def upload_images(image_urls: list[str], folder: str = "dira-bot", max_workers: int = 4) -> list[str]:
    """Upload multiple images in parallel. Returns list of permanent URLs (skips failures)."""
    if not CLOUDINARY_CLOUD_NAME or not image_urls:
        return image_urls  # Pass through originals if Cloudinary not configured

    permanent_urls = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_url = {
            pool.submit(upload_image, url, folder): url for url in image_urls
        }
        for future in as_completed(future_to_url):
            original = future_to_url[future]
            result = future.result()
            # Keep permanent URL if upload succeeded, otherwise keep original
            permanent_urls.append(result if result else original)

    return permanent_urls
