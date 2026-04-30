"""
Hugging Face Inference API client for hook-tailored image generation.
"""

from __future__ import annotations

import io
import os

import requests
from PIL import Image

HF_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_T2I_MODEL = os.getenv(
    "HF_IMAGE_MODEL",
    "stabilityai/stable-diffusion-xl-base-1.0",
)


def generate_tailored_image(recipe_name: str, hook: str, fallback_image: Image.Image | None = None) -> Image.Image | None:
    if not HF_TOKEN:
        return None
    prompt = (
        f"Pinterest food photo, vertical composition, {recipe_name}. "
        f"Visual mood inspired by: {hook}. Natural lighting, appetizing plating, high detail."
    )
    url = f"https://api-inference.huggingface.co/models/{HF_T2I_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception:
        return fallback_image
