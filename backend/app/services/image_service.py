import re
import io
import time
import urllib.parse
import base64
import logging
import requests
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Patterns that signal an image generation prompt
IMAGE_GEN_PATTERNS = [
    r"^\s*(?:generate|create|draw|make|paint|render)\s+(?:an?\s+)?(?:image|picture|photo|illustration|artwork|drawing)\s+(?:of\s+)?(.+)",
    r"^\s*(?:draw|paint|illustrate)\s+(?:me\s+)?(?:a|an)?\s*(.+)",
    r"^\s*(?:image|picture|photo)\s+of\s+(.+)",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in IMAGE_GEN_PATTERNS]


def _strip_watermark(img_bytes: bytes) -> bytes:
    """Uses Pillow to cleanly eliminate the bottom logo badge if present."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        # 68-72px cleanly eliminates any corner logo badge
        crop_px = max(68, int(h * 0.088))
        cropped = img.crop((0, 0, w, h - crop_px))
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=95)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Watermark strip skipped (PIL error): {e}")
        return img_bytes


class ImageService:
    """Multi-provider image generation: AI Horde (zero watermark, no IP block) + Pollinations fallback."""

    @staticmethod
    def detect_image_request(prompt: str) -> Tuple[bool, str]:
        """Detects if user is asking to generate/draw an image.

        Returns (is_image_request, extracted_subject).
        """
        clean_p = prompt.strip()
        for pat in COMPILED_PATTERNS:
            m = pat.match(clean_p)
            if m:
                subject = m.group(1).strip()
                return True, subject
        return False, ""

    @staticmethod
    def _generate_aihorde(prompt: str) -> Optional[Dict[str, Any]]:
        """Generates an image via AI Horde (Stable Diffusion). 100% watermark-free, no rate limit."""
        try:
            logger.info(f"Submitting image request to AI Horde for: '{prompt}'...")
            payload = {
                "prompt": f"{prompt}, high quality, sharp focus, masterpiece, 4k",
                "params": {"steps": 25, "width": 512, "height": 512, "n": 1},
                "nsfw": False,
            }
            headers = {
                "Content-Type": "application/json",
                "apikey": "0000000000",
                "Client-Agent": "MM-Assistant:1.0:student@capstone.local",
            }
            sub = requests.post("https://aihorde.net/api/v2/generate/async", json=payload, headers=headers, timeout=10)
            if sub.status_code != 202:
                logger.warning(f"AI Horde submit returned HTTP {sub.status_code}")
                return None

            req_id = sub.json().get("id")
            if not req_id:
                return None

            status_url = f"https://aihorde.net/api/v2/generate/status/{req_id}"
            # Poll up to 10 iterations (~20s max)
            for _ in range(10):
                time.sleep(2)
                st_res = requests.get(status_url, headers=headers, timeout=10)
                if st_res.status_code == 200:
                    data = st_res.json()
                    if data.get("done") and data.get("generations"):
                        img_url = data["generations"][0].get("img")
                        if img_url:
                            img_r = requests.get(img_url, timeout=15)
                            if img_r.status_code == 200:
                                img_bytes = img_r.content
                                b64_str = base64.b64encode(img_bytes).decode("utf-8")
                                logger.info("AI Horde generated image successfully (watermark-free).")
                                return {
                                    "type": "generated_image",
                                    "prompt": prompt,
                                    "url": img_url,
                                    "base64": b64_str,
                                    "format": "image/webp",
                                    "size": len(img_bytes),
                                }
                    elif data.get("faulted"):
                        logger.warning("AI Horde job faulted.")
                        break
            return None
        except Exception as e:
            logger.warning(f"AI Horde generation error: {e}")
            return None

    @staticmethod
    def _generate_pollinations(prompt: str) -> Optional[Dict[str, Any]]:
        """Fallback to Pollinations with automatic 68px watermark cropping."""
        try:
            logger.info(f"Attempting fallback image generation with Pollinations for: '{prompt}'...")
            encoded_prompt = urllib.parse.quote(prompt.strip())
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"
            resp = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            if resp.status_code == 200:
                img_bytes = _strip_watermark(resp.content)
                b64_str = base64.b64encode(img_bytes).decode("utf-8")
                logger.info("Pollinations generated image successfully.")
                return {
                    "type": "generated_image",
                    "prompt": prompt,
                    "url": image_url,
                    "base64": b64_str,
                    "format": "image/jpeg",
                    "size": len(img_bytes),
                }
            else:
                logger.warning(f"Pollinations returned HTTP {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Pollinations fallback failed: {e}")
            return None

    @staticmethod
    def generate_image(prompt: str) -> Optional[Dict[str, Any]]:
        """Generates an image using AI Horde first, then Pollinations fallback."""
        # 1. Try AI Horde (Fast, Stable Diffusion, 100% watermark-free, no rate limit)
        res = ImageService._generate_aihorde(prompt)
        if res:
            return res

        # 2. Fallback to Pollinations (with Pillow watermark removal)
        res = ImageService._generate_pollinations(prompt)
        if res:
            return res

        logger.error(f"All image generators failed for prompt: '{prompt}'")
        return None


image_service = ImageService()
